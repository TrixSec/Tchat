"""
WebSocket chat client for connecting to Tchat server.
Supports real-time messaging, receiving system notifications, and command processing.
Environment variables:
  - TCHAT_SERVER: Server URL (default: wss://tchat-swad.onrender.com)
  - TCHAT_PORT: Server port (optional, required for ws:// connections)
"""
import asyncio
import json
import websockets
import os

# Default server configuration
DEFAULT_SERVER = "wss://tchat-swad.onrender.com"
MESSAGE_TYPE_CHAT = "chat"
MESSAGE_TYPE_SYSTEM = "system"
MESSAGE_TYPE_ERROR = "error"

# Get connection details from environment
username = input("Enter username: ")
server = os.getenv("TCHAT_SERVER", DEFAULT_SERVER)
port = os.getenv("TCHAT_PORT", "")
port_str = f":{port}" if port else ""
uri = f"{server}{port_str}/ws" if not port else f"{server}/ws"

print(f"Connecting to {uri}...")

async def receive(websocket):
    """
    Listen for incoming messages from the server and display them.
    Handles chat messages, system notifications, and error messages.
    """
    while True:
        try:
            data = await websocket.recv()
            try:
                message = json.loads(data)
            except json.JSONDecodeError as e:
                print(f"\n[ERROR] Failed to parse server message: {e}")
                continue

            msg_type = message.get("type", MESSAGE_TYPE_SYSTEM)

            if msg_type == MESSAGE_TYPE_CHAT:
                print(f"\n[{message.get('user', 'Unknown')}]: {message.get('message', '')}")

            elif msg_type == MESSAGE_TYPE_SYSTEM:
                print(f"\n[SYSTEM]: {message.get('message', '')}")

            elif msg_type == MESSAGE_TYPE_ERROR:
                print(f"\n[ERROR]: {message.get('message', '')}")

        except Exception as e:
            print(f"\n[ERROR] Connection lost: {e}")
            break

async def send(websocket):
    """Send user input to the server line by line."""
    while True:
        try:
            msg = await asyncio.to_thread(input, "")

            if msg.strip():
                await websocket.send(msg)
        except Exception as e:
            print(f"\n[ERROR] Failed to send message: {e}")
            break

async def main():
    """Connect to the chat server and run send/receive concurrently."""
    try:
        async with websockets.connect(uri) as websocket:

            await websocket.send(json.dumps({
                "username": username
            }))

            print("Connected!")

            await asyncio.gather(
                receive(websocket),
                send(websocket)
            )
    except ConnectionRefusedError:
        print("\n[ERROR] Connection refused - server not running")
        print("\nTo connect locally:")
        print("  TCHAT_SERVER=ws://localhost TCHAT_PORT=8765 python client.py")
        print("\nTo connect to Render:")
        print("  python client.py")
    except Exception as e:
        print(f"\n[ERROR] Connection error: {e}")
        print("\nTo connect locally:")
        print("  TCHAT_SERVER=ws://localhost TCHAT_PORT=8765 python client.py")
        print("\nTo connect to Render:")
        print("  python client.py")

if __name__ == "__main__":
    asyncio.run(main())