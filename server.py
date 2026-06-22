"""
WebSocket-based chat server using aiohttp.
Supports direct messaging, username changes, and command processing.
All chat and system events are logged to chat.log for persistence.
"""
import asyncio
import json
import os
from datetime import datetime
from aiohttp import web

clients = {}

# Command constants for command processing
COMMAND_USERS = "/users"
COMMAND_COUNT = "/count"
COMMAND_HELP = "/help"
COMMAND_NICK = "/nick"
COMMAND_DM = "/dm"
COMMAND_QUIT = "/quit"

# Message type constants
MSG_TYPE_CHAT = "chat"
MSG_TYPE_SYSTEM = "system"
MSG_TYPE_ERROR = "error"

def get_time():
    """Return current time in HH:MM:SS format for logging."""
    return datetime.now().strftime("%H:%M:%S")

def write_log(text):
    """Write timestamped text to chat.log file."""
    try:
        with open("chat.log", "a", encoding="utf-8") as f:
            f.write(text + "\n")
    except IOError as e:
        print(f"[ERROR] Failed to write to chat.log: {e}")

def log_event(event_type, username, message):
    """Log events to both console and chat.log with consistent formatting."""
    timestamp = get_time()
    log_msg = f"[{timestamp}] [{event_type}] {username}: {message}"
    print(log_msg)
    write_log(log_msg)

async def broadcast(message):
    """Send message to all connected clients. Silently ignore failures per client."""
    if clients:
        await asyncio.gather(
            *[ws.send_str(json.dumps(message)) for ws in clients.values()],
            return_exceptions=True
        )

async def websocket_handler(request):
    """
    Handle WebSocket connections for chat. Manages user join/leave, processes commands,
    and broadcasts messages to all connected clients.
    """
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    username = None
    try:
        # Receive initial connection message containing username
        data_msg = await ws.receive()
        if data_msg.type == web.WSMsgType.CLOSE:
            await ws.close()
            return ws
        if data_msg.type != web.WSMsgType.TEXT:
            await ws.close()
            return ws

        # Parse and validate username from initial message
        try:
            data = json.loads(data_msg.data)
        except json.JSONDecodeError as e:
            await ws.send_str(json.dumps({
                "type": MSG_TYPE_ERROR,
                "message": "Invalid JSON format"
            }))
            await ws.close()
            return ws

        username = data.get("username", "").strip()

        if not username:
            await ws.send_str(json.dumps({
                "type": MSG_TYPE_ERROR,
                "message": "Username is required"
            }))
            await ws.close()
            return ws

        if username in clients:
            await ws.send_str(json.dumps({
                "type": MSG_TYPE_ERROR,
                "message": "Username already exists"
            }))
            await ws.close()
            return ws

        # Register new client and announce join
        clients[username] = ws
        log_event("JOIN", username, "joined the chat")

        await broadcast({
            "type": MSG_TYPE_SYSTEM,
            "message": f"{username} joined the chat"
        })

        # Main message loop - process incoming messages
        async for websocket_message in ws:
            if websocket_message.type != web.WSMsgType.TEXT:
                continue

            message_content = websocket_message.data.strip()
            if not message_content:
                continue

            # Process special commands
            if message_content == COMMAND_USERS:
                await ws.send_str(json.dumps({
                    "type": MSG_TYPE_SYSTEM,
                    "message": "Online Users: " + ", ".join(clients.keys())
                }))
                continue

            if message_content == COMMAND_COUNT:
                await ws.send_str(json.dumps({
                    "type": MSG_TYPE_SYSTEM,
                    "message": f"Online Users Count: {len(clients)}"
                }))
                continue

            if message_content == COMMAND_HELP:
                await ws.send_str(json.dumps({
                    "type": MSG_TYPE_SYSTEM,
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

            # Handle nickname change command
            if message_content.startswith(COMMAND_NICK + " "):
                new_name = message_content.split(" ", 1)[1].strip()
                if not new_name:
                    await ws.send_str(json.dumps({
                        "type": MSG_TYPE_ERROR,
                        "message": "New username cannot be empty"
                    }))
                    continue
                if new_name in clients:
                    await ws.send_str(json.dumps({
                        "type": MSG_TYPE_ERROR,
                        "message": "Username already exists"
                    }))
                    continue
                old_name = username
                del clients[username]
                clients[new_name] = ws
                username = new_name
                log_event("NICK_CHANGE", new_name, f"changed from {old_name}")
                await broadcast({
                    "type": MSG_TYPE_SYSTEM,
                    "message": f"{old_name} changed name to {new_name}"
                })
                continue

            # Handle direct message command
            if message_content.startswith(COMMAND_DM + " "):
                parts = message_content.split(" ", 2)
                if len(parts) < 3:
                    await ws.send_str(json.dumps({
                        "type": MSG_TYPE_ERROR,
                        "message": "Usage: /dm username message"
                    }))
                    continue
                target_user = parts[1]
                dm_message_content = parts[2]
                if target_user not in clients:
                    await ws.send_str(json.dumps({
                        "type": MSG_TYPE_ERROR,
                        "message": "User not found"
                    }))
                    continue
                await clients[target_user].send_str(json.dumps({
                    "type": MSG_TYPE_SYSTEM,
                    "message": f"[DM from {username}] {dm_message_content}"
                }))
                await ws.send_str(json.dumps({
                    "type": MSG_TYPE_SYSTEM,
                    "message": f"[DM to {target_user}] {dm_message_content}"
                }))
                log_event("DM", username, f"to {target_user}: {dm_message_content}")
                continue

            # Regular chat message - broadcast to all users
            log_event("CHAT", username, message_content)
            await broadcast({
                "type": MSG_TYPE_CHAT,
                "user": username,
                "message": f"[{get_time()}] {message_content}"
            })

    except Exception as e:
        print(f"[ERROR] WebSocket handler error: {type(e).__name__}: {e}")

    finally:
        # Clean up on disconnect
        if username and username in clients:
            del clients[username]
            log_event("LEAVE", username, "left the chat")
            await broadcast({
                "type": MSG_TYPE_SYSTEM,
                "message": f"{username} left the chat"
            })

    return ws

async def health_check(request):
    """Health check endpoint - returns OK if server is running."""
    return web.Response(text="OK")

def create_app():
    """Create and configure the aiohttp application with WebSocket and health check routes."""
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/ws", websocket_handler)
    return app

def main():
    """Start the WebSocket chat server."""
    port = int(os.environ.get("PORT", 8765))
    app = create_app()
    print(f"[INFO] Starting chat server on 0.0.0.0:{port}")
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
