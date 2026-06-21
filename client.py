import asyncio
import json
import websockets

username = input("Enter username: ")

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
    uri = "wss://tchat-swad.onrender.com/ws"

    async with websockets.connect(uri) as websocket:

        await websocket.send(json.dumps({
            "username": username
        }))

        print("Connected!")

        await asyncio.gather(
            receive(websocket),
            send(websocket)
        )

asyncio.run(main())