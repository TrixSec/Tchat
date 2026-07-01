import asyncio
import json
import os
import sys
import time
import argparse
import logging
import websockets

# Add parent directory to sys.path so we can import shared modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.protocol import (
    MSG_CHAT, MSG_DM, MSG_REPLY, MSG_PRESENCE, MSG_FILE_OFFER, MSG_FILE_ACCEPT,
    MSG_FILE_REJECT, MSG_FILE_CHUNK, MSG_FILE_END, MSG_FILE_CANCEL, MSG_HEARTBEAT,
    MSG_SYSTEM, MSG_ERROR, make_message, serialize_message, deserialize_message
)
from presence import PresenceManager
from relay import TelegramRelay
from files import FileTransferManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class TermChatServer:
    def __init__(self):
        # Maps username -> websocket
        self.clients = {}
        # Maps username -> float (last seen timestamp)
        self.last_seen = {}
        
        self.presence_mgr = PresenceManager()
        self.file_mgr = FileTransferManager()
        self.telegram_relay = TelegramRelay(self.handle_telegram_message_callback)
        
        self.message_counter = 100
        
    def handle_telegram_message_callback(self, username, text):
        """Callback triggered when a message is received from a user's Telegram bot."""
        asyncio.create_task(self.broadcast_telegram_message(username, text))
        
    async def broadcast_telegram_message(self, username, text):
        self.message_counter += 1
        msg_id = self.message_counter
        
        # Broadcast the message as [Telegram] Alice: message
        msg = make_message(
            msg_type=MSG_CHAT,
            sender=f"[Telegram] {username}",
            content=text,
            msg_id=msg_id
        )
        
        logging.info(f"Telegram message broadcast from {username}: {text}")
        await self.broadcast(msg)

    async def broadcast(self, message, exclude_user=None):
        """Broadcasts a serialized message to all connected clients."""
        serialized = serialize_message(message)
        coros = []
        for username, ws in self.clients.items():
            if username != exclude_user:
                coros.append(ws.send(serialized))
        if coros:
            await asyncio.gather(*coros, return_exceptions=True)

    async def handle_client(self, websocket):
        username = None
        try:
            # 1. Handshake - receive registration message
            handshake_raw = await websocket.recv()
            handshake = json.loads(handshake_raw)
            username = handshake.get("username", "").strip()
            
            if not username:
                await websocket.send(serialize_message(
                    make_message(MSG_ERROR, "Server", "Username is required")
                ))
                await websocket.close()
                return

            if username in self.clients or "[Telegram]" in username:
                await websocket.send(serialize_message(
                    make_message(MSG_ERROR, "Server", "Username already exists or is invalid")
                ))
                await websocket.close()
                return

            # Register connection
            self.clients[username] = websocket
            self.last_seen[username] = time.time()
            self.presence_mgr.update_presence(username, "online")
            
            # If they passed Telegram settings, register them
            tg_token = handshake.get("telegram_token")
            tg_chat_id = handshake.get("telegram_chat_id")
            if tg_token and tg_chat_id:
                self.telegram_relay.register_user(username, tg_token, tg_chat_id)
                logging.info(f"Registered Telegram bot for {username}")

            # Notify others
            join_msg = make_message(MSG_SYSTEM, "Server", f"{username} has joined the chat")
            await self.broadcast(join_msg)
            
            # Send current presence list to the new user
            online_users = self.presence_mgr.get_online_users_summary()
            await websocket.send(serialize_message(
                make_message(MSG_SYSTEM, "Server", f"Online now: {online_users}")
            ))

            logging.info(f"User {username} connected.")

            # 2. Main message loop
            async for raw_msg in websocket:
                self.last_seen[username] = time.time()
                try:
                    msg = deserialize_message(raw_msg)
                except Exception:
                    continue

                msg_type = msg.get("type")
                
                if msg_type == MSG_HEARTBEAT:
                    # Heartbeat handled simply by updating self.last_seen
                    continue
                    
                elif msg_type == MSG_PRESENCE:
                    status = msg.get("content", "online")
                    message = msg.get("extra", {}).get("message", "")
                    self.presence_mgr.update_presence(username, status, message)
                    
                    # Notify everyone of presence change
                    online_summary = self.presence_mgr.get_online_users_summary()
                    await self.broadcast(make_message(
                        MSG_SYSTEM, "Server", f"{username} status updated to: {status} ({message})" if message else f"{username} is now {status}"
                    ))
                    
                elif msg_type == MSG_CHAT:
                    content = msg.get("content", "").strip()
                    
                    if content.startswith("/"):
                        parts = content.split(" ", 1)
                        cmd = parts[0]
                        arg = parts[1].strip() if len(parts) > 1 else ""
                        
                        if cmd == "/help":
                            help_text = (
                                "Available Server Commands:\n"
                                "  /help   - Show this help message\n"
                                "  /users  - List all online users and their presence status\n"
                                "  /count  - Show the number of active connections"
                            )
                            await websocket.send(serialize_message(
                                make_message(MSG_SYSTEM, "Server", help_text)
                            ))
                        elif cmd == "/users":
                            online_users = self.presence_mgr.get_online_users_summary()
                            await websocket.send(serialize_message(
                                make_message(MSG_SYSTEM, "Server", f"Online now: {online_users}")
                            ))
                        elif cmd == "/count":
                            count = len(self.clients)
                            await websocket.send(serialize_message(
                                make_message(MSG_SYSTEM, "Server", f"Active connections: {count}")
                            ))
                        else:
                            await websocket.send(serialize_message(
                                make_message(MSG_ERROR, "Server", f"Unknown server command: {cmd}")
                            ))
                        continue
                        
                    self.message_counter += 1
                    msg_id = self.message_counter
                    
                    # Construct chat message with ID
                    out_msg = make_message(
                        msg_type=MSG_CHAT,
                        sender=username,
                        content=content,
                        msg_id=msg_id
                    )
                    await self.broadcast(out_msg)
                    
                    # Check for offline mentions
                    words = content.split(" ")
                    for word in words:
                        if word.startswith("@") and len(word) > 1:
                            mentioned_user = word[1:]
                            # Check if user is offline but has Telegram config
                            if mentioned_user not in self.clients and self.telegram_relay.get_user_config(mentioned_user):
                                await self.telegram_relay.send_offline_message(
                                    mentioned_user,
                                    f"[Mention from {username} in chat]: {content}"
                                )
                                
                elif msg_type == MSG_REPLY:
                    content = msg.get("content", "")
                    reply_to = msg.get("reply_to")
                    self.message_counter += 1
                    msg_id = self.message_counter
                    
                    out_msg = make_message(
                        msg_type=MSG_REPLY,
                        sender=username,
                        content=content,
                        reply_to=reply_to,
                        msg_id=msg_id
                    )
                    await self.broadcast(out_msg)
                    
                elif msg_type == MSG_DM:
                    content = msg.get("content", "")
                    target = msg.get("target")
                    self.message_counter += 1
                    msg_id = self.message_counter
                    
                    if target in self.clients:
                        # Relay to target
                        out_msg = make_message(
                            msg_type=MSG_DM,
                            sender=username,
                            content=content,
                            target=target,
                            msg_id=msg_id
                        )
                        await self.clients[target].send(serialize_message(out_msg))
                        
                        # Acknowledge back to sender (so sender UI displays the sent DM)
                        ack_msg = make_message(
                            msg_type=MSG_DM,
                            sender=username,
                            content=content,
                            target=target,
                            msg_id=msg_id
                        )
                        await websocket.send(serialize_message(ack_msg))
                    else:
                        # Target offline - try forwarding to Telegram
                        if self.telegram_relay.get_user_config(target):
                            success = await self.telegram_relay.send_offline_message(
                                target,
                                f"[DM from {username}]: {content}"
                            )
                            if success:
                                await websocket.send(serialize_message(
                                    make_message(MSG_SYSTEM, "Server", f"{target} is offline. Message forwarded to Telegram.")
                                ))
                                # Still acknowledge the DM locally
                                ack_msg = make_message(
                                    msg_type=MSG_DM,
                                    sender=username,
                                    content=content,
                                    target=target,
                                    msg_id=msg_id
                                )
                                await websocket.send(serialize_message(ack_msg))
                            else:
                                await websocket.send(serialize_message(
                                    make_message(MSG_ERROR, "Server", f"User {target} is offline and Telegram delivery failed.")
                                ))
                        else:
                            await websocket.send(serialize_message(
                                make_message(MSG_ERROR, "Server", f"User {target} is offline and has no Telegram bridge.")
                            ))
                            
                # File transfer coordination
                elif msg_type in [MSG_FILE_OFFER, MSG_FILE_ACCEPT, MSG_FILE_REJECT, MSG_FILE_CHUNK, MSG_FILE_END, MSG_FILE_CANCEL]:
                    file_id = msg.get("file_id")
                    target = msg.get("target")
                    
                    if msg_type == MSG_FILE_OFFER:
                        filename = msg.get("filename")
                        filesize = msg.get("filesize")
                        self.file_mgr.register_offer(file_id, username, target, filename, filesize)
                        
                        # Route offer to target client, or broadcast if target is None (public transfer)
                        offer_msg = make_message(
                            msg_type=MSG_FILE_OFFER,
                            sender=username,
                            target=target,
                            file_id=file_id,
                            extra={"filename": filename, "filesize": filesize}
                        )
                        if target:
                            if target in self.clients:
                                await self.clients[target].send(serialize_message(offer_msg))
                            else:
                                await websocket.send(serialize_message(
                                    make_message(MSG_ERROR, "Server", f"User {target} is offline. Cannot offer file.")
                                ))
                        else:
                            await self.broadcast(offer_msg, exclude_user=username)
                            
                    elif msg_type == MSG_FILE_ACCEPT:
                        if self.file_mgr.mark_accepted(file_id, username):
                            transfer = self.file_mgr.get_transfer(file_id)
                            sender_user = transfer["sender"]
                            if sender_user in self.clients:
                                accept_msg = make_message(MSG_FILE_ACCEPT, username, file_id=file_id, target=sender_user)
                                await self.clients[sender_user].send(serialize_message(accept_msg))
                                
                    elif msg_type == MSG_FILE_REJECT:
                        transfer = self.file_mgr.get_transfer(file_id)
                        if transfer:
                            sender_user = transfer["sender"]
                            self.file_mgr.remove_transfer(file_id)
                            if sender_user in self.clients:
                                reject_msg = make_message(MSG_FILE_REJECT, username, file_id=file_id)
                                await self.clients[sender_user].send(serialize_message(reject_msg))
                                
                    elif msg_type == MSG_FILE_CHUNK:
                        transfer = self.file_mgr.get_transfer(file_id)
                        if transfer and transfer["accepted"]:
                            # Forward chunk to recipient
                            recipient = transfer["recipient"]
                            if recipient in self.clients:
                                chunk_msg = make_message(
                                    MSG_FILE_CHUNK, username, 
                                    content=msg.get("content"), # base64 data
                                    file_id=file_id,
                                    extra={"chunk_index": msg.get("extra", {}).get("chunk_index")}
                                )
                                await self.clients[recipient].send(serialize_message(chunk_msg))
                                
                    elif msg_type == MSG_FILE_END:
                        transfer = self.file_mgr.get_transfer(file_id)
                        if transfer:
                            recipient = transfer["recipient"]
                            self.file_mgr.remove_transfer(file_id)
                            if recipient in self.clients:
                                end_msg = make_message(MSG_FILE_END, username, file_id=file_id)
                                await self.clients[recipient].send(serialize_message(end_msg))
                                
                    elif msg_type == MSG_FILE_CANCEL:
                        transfer = self.file_mgr.get_transfer(file_id)
                        if transfer:
                            recipient = transfer["recipient"]
                            sender_user = transfer["sender"]
                            self.file_mgr.remove_transfer(file_id)
                            
                            # Notify both ends
                            cancel_msg = make_message(MSG_FILE_CANCEL, username, file_id=file_id)
                            if recipient and recipient in self.clients and recipient != username:
                                await self.clients[recipient].send(serialize_message(cancel_msg))
                            if sender_user and sender_user in self.clients and sender_user != username:
                                await self.clients[sender_user].send(serialize_message(cancel_msg))

        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logging.error(f"Error handling client {username}: {e}")
        finally:
            if username and username in self.clients:
                del self.clients[username]
                if username in self.last_seen:
                    del self.last_seen[username]
                self.presence_mgr.remove_user(username)
                
                # Broadcast leave notification
                leave_msg = make_message(MSG_SYSTEM, "Server", f"{username} has left the chat")
                await self.broadcast(leave_msg)
                logging.info(f"User {username} disconnected.")

    async def heartbeat_check_loop(self):
        """Monitors clients and closes connections that fail to communicate within 45 seconds."""
        while True:
            await asyncio.sleep(10)
            now = time.time()
            for username, ws in list(self.clients.items()):
                last_seen = self.last_seen.get(username, now)
                if now - last_seen > 45: # 45 seconds timeout
                    logging.info(f"Client {username} timed out. Closing connection.")
                    try:
                        await ws.close()
                    except Exception:
                        pass

    async def start(self, port):
        # Start heartbeat monitor
        asyncio.create_task(self.heartbeat_check_loop())
        
        logging.info(f"Starting TermChat Server on port {port}...")
        async with websockets.serve(self.handle_client, "0.0.0.0", port):
            await asyncio.Future() # keep server running

def main():
    parser = argparse.ArgumentParser(description="TermChat v2 Server")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8765)), help="Port to bind server")
    args = parser.parse_args()
    
    server = TermChatServer()
    try:
        asyncio.run(server.start(args.port))
    except KeyboardInterrupt:
        server.telegram_relay.shutdown()
        logging.info("Server shutting down.")

if __name__ == "__main__":
    main()
