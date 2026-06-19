import asyncio
import websockets
import sys
import os

async def receive_messages(websocket):
    # Constantly listen for messages from server and print them
    try:
        async for message in websocket:
            print(f"\r{message}")
            print("You: ", end="", flush=True)
    except websockets.exceptions.ConnectionClosed:
        print("\n[Disconnected from server]")
        os._exit(0)

async def send_messages(websocket):
    # Constantly wait for user to type and send to server
    loop = asyncio.get_event_loop()
    while True:
        try:
            message = await loop.run_in_executor(None, input, "You: ")
            message = message.strip()

            if not message:
                continue

            await websocket.send(message)

            # Handle /quit locally
            if message == "/quit":
                break

            # Handle /clear locally
            if message == "/clear":
                os.system("cls" if os.name == "nt" else "clear")

        except (KeyboardInterrupt, EOFError):
            await websocket.send("/quit")
            break

async def main():
    host = "localhost"
    port = 8765

    try:
        async with websockets.connect(f"ws://{host}:{port}") as websocket:
            
            # Keep asking for username until it's accepted
            while True:
                username = input("Enter your username: ").strip()
                if not username:
                    print("Username cannot be empty.")
                    continue

                await websocket.send(username)
                first_response = str(await websocket.recv())

                if first_response.startswith("ERROR"):
                    print(first_response)
                    continue  # ask again, same connection
                else:
                    print(first_response)
                    break  # username accepted, move on

            # Run both tasks at the same time
            receive_task = asyncio.create_task(receive_messages(websocket))
            send_task = asyncio.create_task(send_messages(websocket))

            await asyncio.gather(receive_task, send_task)

    except ConnectionRefusedError:
        print("Could not connect. Is the server running?")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())