import asyncio
import json
import websockets
import os

username = input("Enter username: ")
server = os.getenv("TCHAT_SERVER", "wss://tchat-swad.onrender.com")
port = os.getenv("TCHAT_PORT", "")
port_str = f":{port}" if port else ""
uri = f"{server}{port_str}/ws" if not port else f"{server}/ws"

print(f"Connecting to {uri}...")

async def receive(websocket):
    while True:
        try:
            data = await websocket.recv()
            data = json.loads(data)

            if data["type"] == "chat":
                print(f"\n[{data['user']}]: {data['message']}")

            elif data["type"] == "system":
                print(f"\n[SYSTEM]: {data['message']}")

            elif data["type"] == "error":
                print(f"\n[ERROR]: {data['message']}")

        except:
            break

async def send(websocket):
    while True:
        msg = await asyncio.to_thread(input, "")

        if msg.strip():
            await websocket.send(msg)

async def main():
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
    except Exception as e:
        print(f"Connection error: {e}")
        print("\nTo connect locally: TCHAT_SERVER=ws://localhost TCHAT_PORT=8765 python client.py")
        print("To connect to Render: python client.py")

asyncio.run(main())