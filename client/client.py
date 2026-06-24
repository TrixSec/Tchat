import asyncio
import json
import websockets
import os
import sys

from client.ui import print_message, console
from client.history import HistoryManager
from shared.models import Message
from client.file_transfer import FileTransferManager
from client.status_bar import status_bar
from client.themes import theme_manager

history_manager = HistoryManager()

username = input("Enter username: ")
file_transfer_manager = FileTransferManager(username)

status_bar.update(username=username, theme=theme_manager.current_theme)

server = os.environ.get(
    "TCHAT_SERVER",
    "ws://localhost"
)

port = os.environ.get(
    "TCHAT_PORT",
    "8765"
)

uri = f"{server}:{port}/ws"


console.print(f"Connecting to {uri}...", style="bold blue")


async def receive(websocket):
    while True:
        try:
            data = await websocket.recv()
            data_dict = json.loads(data)
            
            try:
                msg = Message.from_dict(data_dict)
                
                if msg.type.startswith("file_"):
                    await file_transfer_manager.process_message(msg.type, msg, websocket)
                    continue
                    
                if msg.type in ("chat", "system"):
                    msg_type = "system"
                    if msg.type == "chat":
                        status_bar.update(unread_add=1)
                        msg_type = "dm" if msg.metadata and msg.metadata.get("is_dm") else "public"
                    
                    reply_to = msg.metadata.get("reply_to") if msg.metadata else None
                    
                    history_manager.save_message(
                        message_id=msg.id,
                        timestamp=msg.time,
                        username=msg.user,
                        content=msg.content,
                        reply_to=reply_to,
                        message_type=msg_type
                    )
            except Exception:
                pass

            print_message(data_dict)

        except websockets.exceptions.ConnectionClosed:
            console.print("\nConnection closed", style="bold red")
            break

        except Exception as e:
            console.print(f"Receive error: {e}", style="bold red")
            break


async def send(websocket):
    while True:
        try:
            msg = await asyncio.to_thread(
                input,
                ""
            )

            if msg.strip():
                content = msg.strip()
                status_bar.update(unread_clear=True)
                
                if file_transfer_manager.has_pending_offer() and content.lower() in ('y', 'n'):
                    sys.stdout.write("\033[F")
                    sys.stdout.write("\033[K")
                    sys.stdout.flush()
                    await file_transfer_manager.handle_accept_reject(content, websocket)
                    continue
                    
                if content.startswith("/send "):
                    filepath = content[len("/send "):].strip()
                    sys.stdout.write("\033[F")
                    sys.stdout.write("\033[K")
                    sys.stdout.flush()
                    await file_transfer_manager.start_transfer(filepath, websocket)
                    continue
                elif content == "/cancel":
                    sys.stdout.write("\033[F")
                    sys.stdout.write("\033[K")
                    sys.stdout.flush()
                    await file_transfer_manager.handle_cancel(websocket)
                    continue
                if content.startswith("/reply "):
                    parts = content.split(" ", 2)
                    if len(parts) >= 3:
                        try:
                            reply_to_id = int(parts[1])
                            payload = json.dumps({
                                "type": "chat",
                                "content": parts[2],
                                "metadata": {"reply_to": reply_to_id}
                            })
                        except ValueError:
                            console.print("[ERROR] Invalid message ID for reply", style="bold red")
                            continue
                    else:
                        console.print("[ERROR] Usage: /reply <message_id> <text>", style="bold red")
                        continue
                elif content.startswith("/history"):
                    parts = content.split()
                    limit = 20
                    if len(parts) > 1 and parts[1].isdigit():
                        limit = int(parts[1])
                    
                    sys.stdout.write("\033[F")
                    sys.stdout.write("\033[K")
                    sys.stdout.flush()

                    results = history_manager.get_recent(limit)
                    if not results:
                        console.print("No local history found.", style="dim")
                    else:
                        for row in results:
                            msg_id, ts, user, msg_content, reply_to, msg_type = row
                            msg_id_str = msg_id if msg_id is not None else "?"
                            console.print(f"[{msg_id_str}] {user}: {msg_content}")
                    continue
                elif content.startswith("/search"):
                    parts = content.split(" ", 1)
                    if len(parts) > 1:
                        query = parts[1].strip()
                    else:
                        query = ""
                        
                    sys.stdout.write("\033[F")
                    sys.stdout.write("\033[K")
                    sys.stdout.flush()

                    if not query:
                        console.print("[ERROR] Usage: /search <query>", style="bold red")
                        continue

                    results = history_manager.search(query)
                    console.print(f'Results for "{query}"', style="bold cyan")
                    if not results:
                        console.print("No local history found.", style="dim")
                    else:
                        for row in results:
                            msg_id, ts, user, msg_content, reply_to, msg_type = row
                            msg_id_str = msg_id if msg_id is not None else "?"
                            console.print(f"[{msg_id_str}] {user}: {msg_content}")
                    continue
                elif content == "/theme":
                    sys.stdout.write("\033[F")
                    sys.stdout.write("\033[K")
                    sys.stdout.flush()
                    from client.themes import theme_manager
                    console.print(f"Current Theme: {theme_manager.current_theme}")
                    console.print("\nAvailable Themes:")
                    for t in theme_manager.themes.keys():
                        console.print(f"- {t}")
                    continue
                elif content.startswith("/theme "):
                    theme_name = content.split(" ", 1)[1].strip()
                    sys.stdout.write("\033[F")
                    sys.stdout.write("\033[K")
                    sys.stdout.flush()
                    
                    from client.themes import theme_manager
                    if theme_manager.set_theme(theme_name):
                        status_bar.update(theme=theme_manager.current_theme)
                        console.print(f"[*] Theme changed to {theme_name}", style="italic yellow")
                    else:
                        console.print("Invalid theme.")
                        console.print("\nAvailable themes:")
                        for t in theme_manager.themes.keys():
                            console.print(t)
                    continue
                elif content.startswith("/"):
                    # Command
                    payload = json.dumps({
                        "type": "command",
                        "content": content
                    })
                else:
                    # Chat
                    payload = json.dumps({
                        "type": "chat",
                        "content": content
                    })

                # Move cursor up and clear line so typed text is replaced by formatted message
                sys.stdout.write("\033[F")
                sys.stdout.write("\033[K")
                sys.stdout.flush()

                await websocket.send(payload)

        except Exception:
            break


async def main():
    try:
        status_bar.setup()
        async with websockets.connect(uri) as websocket:
            status_bar.update(connected=True)
            # send username
            await websocket.send(
                json.dumps({
                    "username": username
                })
            )

            console.print("\nConnected ✓", style="bold green")
            console.print("Type /help for commands\n", style="dim")

            await asyncio.gather(
                receive(websocket),
                send(websocket)
            )
            
        status_bar.update(connected=False)

    except Exception as e:
        status_bar.update(connected=False)
        console.print(f"Connection error: {e}", style="bold red")
        console.print(
            "\nExample:\nLocal: python -m client.client\nRemote: TCHAT_SERVER=ws://server-ip python -m client.client",
            style="dim"
        )


if __name__ == "__main__":
    asyncio.run(main())