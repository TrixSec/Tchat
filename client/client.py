import asyncio
import json
import os
import sys
import time
import argparse
import base64
import threading
import websockets

# Add parent directory to sys.path so we can import client and shared modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.protocol import (
    MSG_CHAT, MSG_DM, MSG_REPLY, MSG_PRESENCE, MSG_FILE_OFFER, MSG_FILE_ACCEPT,
    MSG_FILE_REJECT, MSG_FILE_CHUNK, MSG_FILE_END, MSG_FILE_CANCEL, MSG_HEARTBEAT,
    MSG_SYSTEM, MSG_ERROR, make_message, serialize_message, deserialize_message
)

from config import load_config, save_config
from history import init_db, save_message, get_history, search_history
from ui import TerminalUI
from autocomplete import autocomplete
from telegram import verify_telegram_bot

# Cross-platform keyboard reading setup
if sys.platform == "win32":
    import msvcrt
    
    def read_keys(queue, loop):
        while True:
            try:
                ch = msvcrt.getch()
                if not ch:
                    continue
                # Ctrl+C
                if ch == b"\x03":
                    loop.call_soon_threadsafe(queue.put_nowait, "KEY_QUIT")
                    break
                elif ch in (b"\x08", b"\x7f"):  # Backspace
                    loop.call_soon_threadsafe(queue.put_nowait, "KEY_BACKSPACE")
                elif ch in (b"\r", b"\n"):
                    loop.call_soon_threadsafe(queue.put_nowait, "KEY_ENTER")
                elif ch == b"\t":
                    loop.call_soon_threadsafe(queue.put_nowait, "KEY_TAB")
                elif ch in (b"\xe0", b"\x00"):  # arrow keys/special keys
                    msvcrt.getch()  # swallow the suffix byte
                    continue
                else:
                    try:
                        char = ch.decode("utf-8")
                        loop.call_soon_threadsafe(queue.put_nowait, char)
                    except UnicodeDecodeError:
                        pass
            except Exception:
                break
else:
    import tty
    import termios
    
    def read_keys(queue, loop):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while True:
                ch = sys.stdin.read(1)
                if not ch:
                    continue
                # Ctrl+C
                if ch == "\x03":
                    loop.call_soon_threadsafe(queue.put_nowait, "KEY_QUIT")
                    break
                elif ch in ("\x7f", "\x08"):
                    loop.call_soon_threadsafe(queue.put_nowait, "KEY_BACKSPACE")
                elif ch in ("\r", "\n"):
                    loop.call_soon_threadsafe(queue.put_nowait, "KEY_ENTER")
                elif ch == "\t":
                    loop.call_soon_threadsafe(queue.put_nowait, "KEY_TAB")
                else:
                    loop.call_soon_threadsafe(queue.put_nowait, ch)
        except Exception:
            pass
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

class TermChatClient:
    def __init__(self, host, port, cmd_username):
        self.config = load_config()
        
        # Load username preference
        self.username = cmd_username or self.config.get("username")
        
        self.host = host or self.config.get("server_address", "ws://localhost:8765").split("://")[1].split(":")[0]
        self.port = port or int(self.config.get("server_address", "ws://localhost:8765").split(":")[-1])
        
        # Initialize SQLite DB
        init_db()
        
        self.theme_name = self.config.get("theme", "dark")
        self.ui = TerminalUI(self.theme_name)
        
        self.websocket = None
        self.connected = False
        
        self.current_presence = "online"
        self.current_custom_status = ""
        self.online_users = []
        
        self.offline_queue = []
        self.active_uploads = {}   # file_id -> filepath
        self.active_downloads = {} # file_id -> { "file_pointer", "received", "total", "filename", "local_path" }
        self.pending_transfer = [None] # wrapper to keep mutable in nested context
        
        self.input_queue = asyncio.Queue()
        self.loop = None
        self.running = True

    async def verify_and_save_config(self):
        """Saves current username and server address back to configuration."""
        self.config["username"] = self.username
        self.config["server_address"] = f"ws://{self.host}:{self.port}"
        save_config(self.config)

    async def upload_file_task(self, file_id, filepath, recipient):
        try:
            filesize = os.path.getsize(filepath)
            chunk_size = 32768  # 32 KB
            chunk_idx = 0
            sent_bytes = 0
            
            self.ui.print_text(f"[File Transfer] Starting upload of {os.path.basename(filepath)}...")
            
            with open(filepath, "rb") as f:
                while self.connected:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                        
                    encoded = base64.b64encode(chunk).decode("utf-8")
                    chunk_msg = make_message(
                        MSG_FILE_CHUNK, self.username,
                        content=encoded,
                        file_id=file_id,
                        target=recipient,
                        extra={"chunk_index": chunk_idx}
                    )
                    await self.websocket.send(serialize_message(chunk_msg))
                    
                    chunk_idx += 1
                    sent_bytes += len(chunk)
                    
                    percent = (sent_bytes / filesize) * 100
                    self.ui.print_text(f"[File Transfer] Uploading {os.path.basename(filepath)}: {percent:.1f}%")
                    await asyncio.sleep(0.01)  # tiny yield
                    
            if self.connected:
                end_msg = make_message(MSG_FILE_END, self.username, file_id=file_id, target=recipient)
                await self.websocket.send(serialize_message(end_msg))
                self.ui.print_text(f"[File Transfer] Uploaded {os.path.basename(filepath)} successfully!")
        except Exception as e:
            self.ui.print_text(f"[File Transfer] Upload error: {e}")
            if self.connected:
                cancel_msg = make_message(MSG_FILE_CANCEL, self.username, file_id=file_id, target=recipient)
                await self.websocket.send(serialize_message(cancel_msg))

    async def receive_loop(self):
        try:
            async for raw_msg in self.websocket:
                try:
                    msg = deserialize_message(raw_msg)
                except Exception:
                    continue
                    
                msg_type = msg.get("type")
                msg_id = msg.get("id")
                sender = msg.get("sender")
                content = msg.get("content")
                timestamp = msg.get("timestamp")
                reply_to = msg.get("reply_to")
                target = msg.get("target")
                
                # Save normal/private chat messages to history
                if msg_type in [MSG_CHAT, MSG_DM, MSG_REPLY]:
                    save_message(msg_id, msg_type, sender, target, content, reply_to, timestamp)
                    
                # Format and print the message
                if msg_type in [MSG_CHAT, MSG_DM, MSG_REPLY, MSG_SYSTEM, MSG_ERROR]:
                    fmt = self.ui.format_message(msg_id, sender, content, msg_type, timestamp, reply_to, target)
                    self.ui.print_text(fmt)
                    
                    # Manage local online user tracking from server system notices
                    if msg_type == MSG_SYSTEM and sender == "Server":
                        if "has joined the chat" in content:
                            joined_user = content.split(" has joined")[0].strip()
                            if joined_user not in self.online_users:
                                self.online_users.append(joined_user)
                        elif "has left the chat" in content:
                            left_user = content.split(" has left")[0].strip()
                            if left_user in self.online_users:
                                self.online_users.remove(left_user)
                        elif "changed name to" in content:
                            parts = content.split(" changed name to ")
                            if len(parts) == 2:
                                old_u, new_u = parts[0].strip(), parts[1].strip()
                                if old_u in self.online_users:
                                    self.online_users.remove(old_u)
                                if new_u not in self.online_users:
                                    self.online_users.append(new_u)
                        elif "Online now: " in content:
                            raw_users = content.replace("Online now: ", "")
                            self.online_users.clear()
                            for item in raw_users.split(","):
                                u = item.strip().split(" ")[0].strip()
                                if u and u not in self.online_users:
                                    self.online_users.append(u)
                                    
                        self.ui.update_status(
                            connected=True, 
                            username=self.username, 
                            presence=self.current_presence, 
                            custom_status=self.current_custom_status, 
                            online_users=", ".join(self.online_users)
                        )
                        self.ui.draw_input_area()
                        
                elif msg_type == MSG_FILE_OFFER:
                    filename = msg["extra"]["filename"]
                    filesize = msg["extra"]["filesize"]
                    self.ui.print_text(f"[File Transfer] {sender} offered file: {filename} ({filesize} bytes).")
                    self.pending_transfer[0] = msg
                    self.ui.prompt = "Accept file? (y/n) > "
                    self.ui.draw_input_area()
                    
                elif msg_type == MSG_FILE_ACCEPT:
                    file_id = msg["file_id"]
                    if file_id in self.active_uploads:
                        filepath = self.active_uploads[file_id]
                        asyncio.create_task(self.upload_file_task(file_id, filepath, sender))
                        
                elif msg_type == MSG_FILE_REJECT:
                    file_id = msg["file_id"]
                    if file_id in self.active_uploads:
                        self.ui.print_text(f"[File Transfer] {sender} rejected file transfer.")
                        del self.active_uploads[file_id]
                        
                elif msg_type == MSG_FILE_CHUNK:
                    file_id = msg["file_id"]
                    if file_id in self.active_downloads:
                        dl = self.active_downloads[file_id]
                        data_bytes = base64.b64decode(content)
                        dl["file_pointer"].write(data_bytes)
                        dl["received"] += len(data_bytes)
                        
                        percent = (dl["received"] / dl["total"]) * 100
                        self.ui.print_text(f"[File Transfer] Downloading {dl['filename']}: {percent:.1f}%")
                        
                elif msg_type == MSG_FILE_END:
                    file_id = msg["file_id"]
                    if file_id in self.active_downloads:
                        dl = self.active_downloads[file_id]
                        dl["file_pointer"].close()
                        self.ui.print_text(f"[File Transfer] Downloaded {dl['filename']} successfully! Saved to: {dl['local_path']}")
                        del self.active_downloads[file_id]
                        
                elif msg_type == MSG_FILE_CANCEL:
                    file_id = msg["file_id"]
                    if file_id in self.active_downloads:
                        dl = self.active_downloads[file_id]
                        dl["file_pointer"].close()
                        try:
                            os.remove(dl["local_path"])
                        except Exception:
                            pass
                        self.ui.print_text(f"[File Transfer] Transfer of {dl['filename']} cancelled by sender.")
                        del self.active_downloads[file_id]
                    if file_id in self.active_uploads:
                        self.ui.print_text(f"[File Transfer] Transfer cancelled by recipient.")
                        del self.active_uploads[file_id]

        except websockets.exceptions.ConnectionClosed:
            pass

    async def heartbeat_loop(self):
        try:
            while self.connected:
                await asyncio.sleep(20)
                await self.websocket.send(serialize_message(make_message(MSG_HEARTBEAT, self.username)))
        except Exception:
            pass

    async def connect_and_run(self):
        attempts = 0
        max_attempts = 5
        delay = 2
        
        uri = f"ws://{self.host}:{self.port}"
        
        while self.running and attempts < max_attempts:
            if attempts > 0:
                self.ui.print_text(f"[System] Connection lost. Retrying... (Attempt {attempts}/{max_attempts})")
                
            try:
                self.ui.update_status(connected=False)
                self.ui.draw_input_area()
                
                async with websockets.connect(uri) as ws:
                    self.websocket = ws
                    self.connected = True
                    attempts = 0  # reset attempts
                    delay = 2     # reset backoff delay
                    
                    self.ui.print_text("[System] Connected to server!")
                    
                    # Handshake registration
                    handshake = {
                        "username": self.username,
                        "telegram_token": self.config.get("telegram", {}).get("bot_token", ""),
                        "telegram_chat_id": self.config.get("telegram", {}).get("chat_id", "")
                    }
                    await ws.send(json.dumps(handshake))
                    
                    self.ui.update_status(
                        connected=True, 
                        username=self.username, 
                        presence=self.current_presence, 
                        custom_status=self.current_custom_status, 
                        online_users=""
                    )
                    self.ui.draw_input_area()
                    
                    # Send offline queued messages
                    while self.offline_queue:
                        queued_msg = self.offline_queue.pop(0)
                        await ws.send(serialize_message(queued_msg))
                        
                    await asyncio.gather(
                        self.receive_loop(),
                        self.heartbeat_loop()
                    )
            except Exception as e:
                self.connected = False
                self.ui.update_status(connected=False)
                self.ui.draw_input_area()
                
                attempts += 1
                if attempts >= max_attempts:
                    self.ui.print_text("[System] Maximum connection attempts reached. Exiting.")
                    self.running = False
                    # Stop loop
                    os._exit(0)
                    break
                await asyncio.sleep(delay)
                delay = min(delay * 1.5, 10)  # capped exponential backoff

    async def input_loop(self):
        while self.running:
            key = await self.input_queue.get()
            
            if key == "KEY_QUIT":
                self.ui.print_text("[System] Quitting...")
                self.running = False
                os._exit(0)
                break
                
            elif key == "KEY_BACKSPACE":
                self.ui.handle_backspace()
                
            elif key == "KEY_TAB":
                # Autocomplete the buffer content
                completed = autocomplete(self.ui.input_buffer, self.online_users)
                self.ui.input_buffer = completed
                self.ui.draw_input_area()
                
            elif key == "KEY_ENTER":
                cmd_line = self.ui.input_buffer.strip()
                self.ui.clear_input()
                
                if not cmd_line:
                    continue
                    
                # 1. Local Slash Commands
                if cmd_line.startswith("/"):
                    parts = cmd_line.split(" ", 1)
                    cmd = parts[0]
                    arg = parts[1].strip() if len(parts) > 1 else ""
                    
                    if cmd == "/clear":
                        os.system("cls" if os.name == "nt" else "clear")
                        self.ui.draw_input_area()
                        
                    elif cmd == "/quit":
                        self.ui.print_text("[System] Quitting...")
                        self.running = False
                        os._exit(0)
                        
                    elif cmd == "/theme":
                        if self.ui.set_theme(arg):
                            self.config["theme"] = arg
                            save_config(self.config)
                            self.ui.print_text(f"[System] Theme updated to '{arg}'.")
                        else:
                            self.ui.print_text("[System] Themes: dark, hacker, dracula, nord.")
                            
                    elif cmd == "/history":
                        hist = get_history(20)
                        self.ui.print_text("--- History (last 20) ---")
                        for r in hist:
                            fmt = self.ui.format_message(r[0], r[2], r[4], r[1], r[6], r[5], r[3])
                            self.ui.print_text(fmt)
                        self.ui.print_text("-------------------------")
                        
                    elif cmd == "/search":
                        if not arg:
                            self.ui.print_text("[System] Usage: /search <query>")
                        else:
                            matches = search_history(arg)
                            self.ui.print_text(f"--- Search Results for '{arg}' ---")
                            for r in matches:
                                fmt = self.ui.format_message(r[0], r[2], r[4], r[1], r[6], r[5], r[3])
                                self.ui.print_text(fmt)
                            self.ui.print_text("----------------------------------")
                            
                    elif cmd == "/status":
                        self.current_presence = arg if arg in ["online", "idle", "offline"] else "online"
                        self.current_custom_status = arg if arg not in ["online", "idle", "offline"] else ""
                        
                        pres_msg = make_message(
                            MSG_PRESENCE, 
                            self.username, 
                            content=self.current_presence, 
                            extra={"message": self.current_custom_status}
                        )
                        if self.connected:
                            await self.websocket.send(serialize_message(pres_msg))
                        else:
                            self.ui.print_text("[System] Offline. Presence status queued.")
                            
                        self.ui.update_status(
                            connected=self.connected, 
                            username=self.username, 
                            presence=self.current_presence, 
                            custom_status=self.current_custom_status, 
                            online_users=", ".join(self.online_users)
                        )
                        self.ui.draw_input_area()
                        
                    elif cmd == "/send":
                        parts = arg.split(" ", 1)
                        if len(parts) == 0 or not parts[0]:
                            self.ui.print_text("[System] Usage: /send [user] <file> OR /send <file>")
                            continue
                            
                        target_user = None
                        filepath = ""
                        if len(parts) == 2:
                            target_user = parts[0]
                            filepath = parts[1]
                        else:
                            filepath = parts[0]
                            
                        filepath = filepath.strip("'\"")
                        if not os.path.exists(filepath):
                            self.ui.print_text(f"[System] File not found: {filepath}")
                            continue
                            
                        filename = os.path.basename(filepath)
                        filesize = os.path.getsize(filepath)
                        file_id = f"file_{int(time.time())}"
                        
                        self.active_uploads[file_id] = filepath
                        
                        offer_msg = make_message(
                            MSG_FILE_OFFER, self.username,
                            target=target_user,
                            file_id=file_id,
                            extra={"filename": filename, "filesize": filesize}
                        )
                        
                        if self.connected:
                            await self.websocket.send(serialize_message(offer_msg))
                            self.ui.print_text(f"[File Transfer] Offered {filename} ({filesize} B) to {target_user or 'all'}...")
                        else:
                            self.ui.print_text("[System] Offline. Cannot offer file.")
                            
                    elif cmd == "/reply":
                        # Command syntax: /reply <msg_id> <content>
                        subparts = arg.split(" ", 1)
                        if len(subparts) < 2:
                            self.ui.print_text("[System] Usage: /reply <msg_id> <message>")
                            continue
                        try:
                            msg_id = int(subparts[0])
                        except ValueError:
                            self.ui.print_text("[System] Invalid message ID.")
                            continue
                        reply_content = subparts[1]
                        
                        reply_msg = make_message(
                            MSG_REPLY, self.username,
                            content=reply_content,
                            reply_to=msg_id
                        )
                        if self.connected:
                            await self.websocket.send(serialize_message(reply_msg))
                        else:
                            self.offline_queue.append(reply_msg)
                            self.ui.print_text("[System] Offline. Reply message queued.")
                            
                    elif cmd == "/dm":
                        # Command syntax: /dm <username> <content>
                        subparts = arg.split(" ", 1)
                        if len(subparts) < 2:
                            self.ui.print_text("[System] Usage: /dm <username> <message>")
                            continue
                        dm_user = subparts[0]
                        dm_content = subparts[1]
                        
                        dm_msg = make_message(
                            MSG_DM, self.username,
                            content=dm_content,
                            target=dm_user
                        )
                        if self.connected:
                            await self.websocket.send(serialize_message(dm_msg))
                        else:
                            self.offline_queue.append(dm_msg)
                            self.ui.print_text("[System] Offline. Direct Message queued.")
                            
                    else:
                        # Forward server commands like /users, /help, /count to server
                        if self.connected:
                            await self.websocket.send(serialize_message(make_message(MSG_CHAT, self.username, content=cmd_line)))
                        else:
                            self.ui.print_text("[System] Offline. Cannot send command.")
                            
                # 2. File Accept/Reject Response handling
                elif self.pending_transfer[0]:
                    ans = cmd_line.lower().strip()
                    transfer = self.pending_transfer[0]
                    file_id = transfer["file_id"]
                    sender = transfer["sender"]
                    filename = transfer["extra"]["filename"]
                    filesize = transfer["extra"]["filesize"]
                    
                    self.pending_transfer[0] = None
                    self.ui.prompt = "> "
                    self.ui.draw_input_area()
                    
                    if ans in ["y", "yes"]:
                        accept_msg = make_message(MSG_FILE_ACCEPT, self.username, file_id=file_id, target=sender)
                        if self.connected:
                            await self.websocket.send(serialize_message(accept_msg))
                            self.ui.print_text(f"[File Transfer] Accepting {filename} from {sender}...")
                            
                            local_path = os.path.join(os.getcwd(), filename)
                            # Handle duplicate filenames locally
                            base, ext = os.path.splitext(filename)
                            c = 1
                            while os.path.exists(local_path):
                                local_path = os.path.join(os.getcwd(), f"{base}_{c}{ext}")
                                c += 1
                                
                            f_ptr = open(local_path, "wb")
                            self.active_downloads[file_id] = {
                                "file_pointer": f_ptr,
                                "received": 0,
                                "total": filesize,
                                "filename": filename,
                                "local_path": local_path
                            }
                        else:
                            self.ui.print_text("[System] Offline. Cannot accept file transfer.")
                    else:
                        reject_msg = make_message(MSG_FILE_REJECT, self.username, file_id=file_id, target=sender)
                        if self.connected:
                            await self.websocket.send(serialize_message(reject_msg))
                        self.ui.print_text(f"[File Transfer] Rejected file transfer from {sender}.")
                        
                # 3. Regular Messaging
                else:
                    chat_msg = make_message(MSG_CHAT, self.username, content=cmd_line)
                    if self.connected:
                        await self.websocket.send(serialize_message(chat_msg))
                    else:
                        self.offline_queue.append(chat_msg)
                        self.ui.print_text("[System] Offline. Chat message buffered.")
            
    async def start(self):
        self.loop = asyncio.get_running_loop()
        
        # Start keyboard listener in daemon thread
        threading.Thread(target=read_keys, args=(self.input_queue, self.loop), daemon=True).start()
        
        # Clear screen and welcome
        os.system("cls" if os.name == "nt" else "clear")
        self.ui.print_text("=====================================")
        self.ui.print_text("       WELCOME TO TERMCHAT V2        ")
        self.ui.print_text("=====================================")
        self.ui.print_text("Type /help to see all available commands.")
        self.ui.print_text("Connecting...")
        
        # Verify username
        if not self.username:
            # Temporarily stop raw reader thread if it interrupts input (it doesn't start processing till input_loop runs, but we do standard input prompt first)
            # Since threads haven't started executing getch loop yet, we can do standard input
            self.username = input("Enter username: ").strip()
            while not self.username:
                self.username = input("Username cannot be empty. Enter username: ").strip()
                
        await self.verify_and_save_config()
        
        # Run connection broker and local prompt processing
        await asyncio.gather(
            self.connect_and_run(),
            self.input_loop()
        )

def main():
    parser = argparse.ArgumentParser(description="TermChat v2 Client")
    parser.add_argument("--host", type=str, default="", help="Server hostname")
    parser.add_argument("--port", type=int, default=0, help="Server port number")
    parser.add_argument("--username", type=str, default="", help="Your chat display name")
    args = parser.parse_args()
    
    client = TermChatClient(args.host, args.port, args.username)
    try:
        asyncio.run(client.start())
    except KeyboardInterrupt:
        # Exit raw terminal settings cleanly
        print("\nExited.")

if __name__ == "__main__":
    main()
