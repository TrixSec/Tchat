import asyncio
import json
import os
from datetime import datetime
from aiohttp import web

clients = {}

def get_time():
    return datetime.now().strftime("%H:%M:%S")

def write_log(text):
    with open("chat.log", "a", encoding="utf-8") as f:
        f.write(text + "\n")

async def broadcast(message):
    if clients:
        await asyncio.gather(
            *[ws.send_str(json.dumps(message)) for ws in clients.values()],
            return_exceptions=True
        )

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    username = None
    try:
        data_msg = await ws.receive()
        if data_msg.type == web.WSMsgType.CLOSE:
            await ws.close()
            return ws
        if data_msg.type != web.WSMsgType.TEXT:
            await ws.close()
            return ws

        data = json.loads(data_msg.data)
        username = data.get("username")

        if not username:
            await ws.send_str(json.dumps({
                "type": "error",
                "message": "Username is required"
            }))
            await ws.close()
            return ws

        if username in clients:
            await ws.send_str(json.dumps({
                "type": "error",
                "message": "Username already exists"
            }))
            await ws.close()
            return ws

        clients[username] = ws

        join_msg = f"[{get_time()}] {username} joined"
        print(join_msg)
        write_log(join_msg)

        await broadcast({
            "type": "system",
            "message": f"{username} joined the chat"
        })

        async for msg in ws:
            if msg.type != web.WSMsgType.TEXT:
                continue

            message = msg.data

            if message == "/users":
                await ws.send_str(json.dumps({
                    "type": "system",
                    "message": "Online Users: " + ", ".join(clients.keys())
                }))
                continue

            if message == "/count":
                await ws.send_str(json.dumps({
                    "type": "system",
                    "message": f"Online Users Count: {len(clients)}"
                }))
                continue

            if message == "/help":
                await ws.send_str(json.dumps({
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

            if message.startswith("/nick "):
                new_name = message.split(" ", 1)[1].strip()
                if not new_name:
                    continue
                if new_name in clients:
                    await ws.send_str(json.dumps({
                        "type": "error",
                        "message": "Username already exists"
                    }))
                    continue
                del clients[username]
                clients[new_name] = ws
                old_name = username
                username = new_name
                await broadcast({
                    "type": "system",
                    "message": f"{old_name} changed name to {new_name}"
                })
                continue

            if message.startswith("/dm "):
                parts = message.split(" ", 2)
                if len(parts) < 3:
                    await ws.send_str(json.dumps({
                        "type": "error",
                        "message": "Usage: /dm username message"
                    }))
                    continue
                target = parts[1]
                dm_message = parts[2]
                if target not in clients:
                    await ws.send_str(json.dumps({
                        "type": "error",
                        "message": "User not found"
                    }))
                    continue
                await clients[target].send_str(json.dumps({
                    "type": "system",
                    "message": f"[DM from {username}] {dm_message}"
                }))
                await ws.send_str(json.dumps({
                    "type": "system",
                    "message": f"[DM to {target}] {dm_message}"
                }))
                continue

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

    return ws

async def health_check(request):
    return web.Response(text="OK")

def create_app():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/ws", websocket_handler)
    return app

def main():
    port = int(os.environ.get("PORT", 8765))
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
