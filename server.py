
import asyncio
import json
import os
import websockets
from datetime import datetime

clients = {}

def get_time():
    return datetime.now().strftime("%H:%M:%S")

def write_log(text):
    with open("chat.log", "a", encoding="utf-8") as f:
        f.write(text + "\n")

async def broadcast(message):
    if clients:
        await asyncio.gather(
            *[ws.send(json.dumps(message)) for ws in clients.values()],
            return_exceptions=True
        )

async def handler(websocket):
    username = None

    try:
        data = await websocket.recv()
        data = json.loads(data)

        username = data["username"]

        if username in clients:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Username already exists"
            }))
            return

        clients[username] = websocket

        join_msg = f"[{get_time()}] {username} joined"
        print(join_msg)
        write_log(join_msg)

        await broadcast({
            "type": "system",
            "message": f"{username} joined the chat"
        })

        async for message in websocket:

            # /users
            if message == "/users":
                await websocket.send(json.dumps({
                    "type": "system",
                    "message": "Online Users: " + ", ".join(clients.keys())
                }))
                continue

            # /count
            if message == "/count":
                await websocket.send(json.dumps({
                    "type": "system",
                    "message": f"Online Users Count: {len(clients)}"
                }))
                continue

            # /help
            if message == "/help":
                await websocket.send(json.dumps({
                    "type": "system",
                    "message":
"""Commands:
/users  - Show online users
/count  - Show online user count
/dm <user> <message> - Private message
/nick <newname> - Change username
/help   - Show help
/quit   - Exit chat
"""
                }))
                continue

            # /nick
            if message.startswith("/nick "):

                new_name = message.split(" ", 1)[1].strip()

                if not new_name:
                    continue

                if new_name in clients:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Username already exists"
                    }))
                    continue

                del clients[username]
                clients[new_name] = websocket

                old_name = username
                username = new_name

                await broadcast({
                    "type": "system",
                    "message": f"{old_name} changed name to {new_name}"
                })

                continue

            # /dm
            if message.startswith("/dm "):

                parts = message.split(" ", 2)

                if len(parts) < 3:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Usage: /dm username message"
                    }))
                    continue

                target = parts[1]
                dm_message = parts[2]

                if target not in clients:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "User not found"
                    }))
                    continue

                await clients[target].send(json.dumps({
                    "type": "system",
                    "message": f"[DM from {username}] {dm_message}"
                }))

                await websocket.send(json.dumps({
                    "type": "system",
                    "message": f"[DM to {target}] {dm_message}"
                }))

                continue

            # Normal chat
            chat_msg = f"[{get_time()}] {username}: {message}"

            print(chat_msg)
            write_log(chat_msg)

            await broadcast({
                "type": "chat",
                "user": username,
                "message": f"[{get_time()}] {message}"
            })

    except Exception as e:
        print("Error:", e)

    finally:
        if username and username in clients:

            del clients[username]

            leave_msg = f"[{get_time()}] {username} left"
            print(leave_msg)
            write_log(leave_msg)

            await broadcast({
                "type": "system",
                "message": f"{username} left the chat"
            })

async def process_request(path, request_headers):
    if path == "/":
        return 200, [("Content-Type", "text/plain")], b"OK"
    return None

async def main():
    port = int(os.environ.get("PORT", 8765))
    async with websockets.serve(handler, "0.0.0.0", port, process_request=process_request):
        print(f"Server running on ws://0.0.0.0:{port}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())

asyncio.run(main())