import asyncio
import json
import os
from datetime import datetime
from aiohttp import web
from server.relay import send_to_telegram, start_telegram_polling
from shared.protocol import create_message
from server.presence import PresenceManager
from server.files import handle_file_message

clients = {}
presence = PresenceManager()
message_counter = 0

def get_time():
    return datetime.now().strftime("%H:%M:%S")

def get_next_id():
    global message_counter
    message_counter += 1
    return message_counter

async def broadcast(message_str: str):
    if clients:
        await asyncio.gather(
            *[ws.send_str(message_str) for ws in clients.values()],
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
            error_msg = create_message("error", "Server", "Username is required")
            await ws.send_str(error_msg)
            await ws.close()
            return ws

        if username in clients:
            error_msg = create_message("error", "Server", "Username already exists")
            await ws.send_str(error_msg)
            await ws.close()
            return ws

        clients[username] = ws
        presence.set_status(username, "Online")
        print(f"[{get_time()}] {username} joined")

        join_broadcast = create_message("system", "Server", f"{username} joined the chat", msg_id=get_next_id())
        await broadcast(join_broadcast)

        async for msg in ws:
            if msg.type != web.WSMsgType.TEXT:
                continue

            try:
                msg_data = json.loads(msg.data)
            except Exception:
                continue

            msg_type = msg_data.get("type")
            content = msg_data.get("content", "")

            if msg_type == "command":
                message = content
                if message == "/users":
                    users_str = ", ".join([f"{u} ({presence.get_status(u)})" for u in clients.keys()])
                    resp = create_message("system", "Server", "Online Users: " + users_str)
                    await ws.send_str(resp)
                    continue

                if message == "/count":
                    resp = create_message("system", "Server", f"Online Users Count: {len(clients)}")
                    await ws.send_str(resp)
                    continue

                if message == "/help":
                    help_text = """Commands:
/users  - Show online users
/count  - Show online user count
/dm <user> <message> - Private message
/nick <newname> - Change username
/status <state> - Change status (Online, Idle, Busy, Coding, Away)
/help   - Show help
/quit   - Exit chat"""
                    resp = create_message("system", "Server", help_text)
                    await ws.send_str(resp)
                    continue

                if message.startswith("/status "):
                    new_status = message.split(" ", 1)[1].strip()
                    if presence.set_status(username, new_status):
                        status_broadcast = create_message("presence", username, presence.get_status(username), msg_id=get_next_id())
                        await broadcast(status_broadcast)
                    else:
                        valid_states = ", ".join(PresenceManager.VALID_STATUSES)
                        err = create_message("error", "Server", f"Invalid status. Valid states: {valid_states}")
                        await ws.send_str(err)
                    continue

                if message.startswith("/nick "):
                    new_name = message.split(" ", 1)[1].strip()
                    if not new_name:
                        continue
                    if new_name in clients:
                        resp = create_message("error", "Server", "Username already exists")
                        await ws.send_str(resp)
                        continue
                    
                    old_status = presence.get_status(username)
                    presence.remove_user(username)
                    presence.set_status(new_name, old_status)
                    
                    del clients[username]
                    clients[new_name] = ws
                    old_name = username
                    username = new_name
                    nick_broadcast = create_message("system", "Server", f"{old_name} changed name to {new_name}", msg_id=get_next_id())
                    await broadcast(nick_broadcast)
                    continue

                if message.startswith("/dm "):
                    parts = message.split(" ", 2)
                    if len(parts) < 3:
                        resp = create_message("error", "Server", "Usage: /dm username message")
                        await ws.send_str(resp)
                        continue
                    target = parts[1]
                    dm_message = parts[2]
                    if target not in clients:
                        resp = create_message("error", "Server", "User not found")
                        await ws.send_str(resp)
                        continue
                    
                    target_msg = create_message("chat", username, dm_message, msg_id=get_next_id(), extra={"is_dm": True})
                    await clients[target].send_str(target_msg)
                    
                    self_msg = create_message("chat", username, f"[DM to {target}] {dm_message}", msg_id=get_next_id(), extra={"is_dm": True})
                    await ws.send_str(self_msg)
                    continue

            elif msg_type == "chat":
                print(f"[{get_time()}] {username}: {content}")
                
                metadata = msg_data.get("metadata", {})
                chat_broadcast = create_message("chat", username, content, msg_id=get_next_id(), extra=metadata)
                await broadcast(chat_broadcast)
                
                if username == "bot":
                    await send_to_telegram(content)
                else:
                    await send_to_telegram(f"[{username}] {content}")

            elif msg_type in ("file_offer", "file_reply", "file_chunk", "file_cancel"):
                await handle_file_message(msg_type, msg_data, username, clients, get_next_id)

    except Exception as e:
        print("Error:", e)

    finally:
        if username and username in clients:
            del clients[username]
            presence.remove_user(username)
            print(f"[{get_time()}] {username} left")
            leave_broadcast = create_message("system", "Server", f"{username} left the chat", msg_id=get_next_id())
            await broadcast(leave_broadcast)

    return ws

async def handle_telegram_message(sender: str, text: str):
    """Callback fired by relay.py when a message arrives from Telegram."""
    global clients
    for username, ws in clients.items():
        if f"@{username}" in text:
            msg_str = create_message(
                "chat", 
                "Telegram", 
                f"[Telegram Mention] {sender}: {text}", 
                msg_id=get_next_id(),
                extra={"is_dm": True}
            )
        else:
            msg_str = create_message(
                "chat", 
                "Telegram", 
                f"[Telegram] {sender}: {text}", 
                msg_id=get_next_id()
            )
        asyncio.create_task(ws.send_str(msg_str))

async def start_background_tasks(app):
    app['telegram_poller'] = asyncio.create_task(start_telegram_polling(handle_telegram_message))

async def cleanup_background_tasks(app):
    app['telegram_poller'].cancel()
    try:
        await app['telegram_poller']
    except asyncio.CancelledError:
        pass

async def health_check(request):
    return web.Response(text="OK")

def create_app():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/ws", websocket_handler)
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    return app

def main():
    port = int(os.environ.get("PORT", 8765))
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
