import asyncio
import websockets
from datetime import datetime

connected_clients={} # stores connected clients in key-value pairs (username:websocket)

def get_time():
    return datetime.now().strftime("%H:%M")

  
async def broadcast(message, exclude=None):
    for username, client in list(connected_clients.items()):
        if client != exclude:
            try:
              await client.send(message)
            except:
             pass
           
async def handler(websocket,username = None):
    
    try:
        # ==========================================
        # USERNAME VALIDATION LOOP
        # ==========================================
        while True:
            username = await websocket.recv()
            username = username.strip()

            if not username:
                await websocket.send("ERROR: Username cannot be empty.")
                continue

            if username in connected_clients:
                await websocket.send("ERROR: Username already taken.")
                continue

            break  # Valid username

        # ==========================================
        # REGISTER USER
        # ==========================================
        connected_clients[username] = websocket

        join_msg = f"[{get_time()}] *** {username} has joined the chat ***"
        print(join_msg)
        await broadcast(join_msg)

        # Welcome message to the new user
        await websocket.send(
            f"[{get_time()}] Welcome {username}! Type /help to see commands."
        )

        # ==========================================
        # MAIN MESSAGE LOOP
        # ==========================================
        async for message in websocket:
            message = message.strip()

            if not message:
                continue

            # --------------------------------------
            # /help
            # --------------------------------------
            if message == "/help":
                help_text = (
                    f"[{get_time()}] Commands:\n"
                    "  /users        - See who is online\n"
                    "  /dm user msg  - Send private message\n"
                    "  /nick newname - Change your username\n"
                    "  /quit         - Leave the chat"
                )
                await websocket.send(help_text)

            # --------------------------------------
            # /users
            # --------------------------------------
            elif message == "/users":
                user_list = ", ".join(connected_clients.keys())
                await websocket.send(
                    f"[{get_time()}] Online now: {user_list}"
                )

            # --------------------------------------
            # /dm username message
            # --------------------------------------
            elif message.startswith("/dm "):
                parts = message.split(" ", 2)

                if len(parts) < 3:
                    await websocket.send(
                        f"[{get_time()}] Usage: /dm username message"
                    )
                else:
                    target = parts[1]
                    dm_text = parts[2]

                    if target not in connected_clients:
                        await websocket.send(
                            f"[{get_time()}] User '{target}' not found."
                        )

                    elif target == username:
                        await websocket.send(
                            f"[{get_time()}] You cannot DM yourself."
                        )

                    else:
                        await connected_clients[target].send(
                            f"[{get_time()}] [DM from {username}]: {dm_text}"
                        )
                        await websocket.send(
                            f"[{get_time()}] [DM to {target}]: {dm_text}"
                        )

            # --------------------------------------
            # /nick newname
            # --------------------------------------
            elif message.startswith("/nick "):
                new_name = message.split(" ", 1)[1].strip()

                if not new_name:
                    await websocket.send(
                        f"[{get_time()}] Usage: /nick newname"
                    )

                elif new_name in connected_clients:
                    await websocket.send(
                        f"[{get_time()}] Username '{new_name}' is already taken."
                    )

                else:
                    old_name = username

                    connected_clients[new_name] = connected_clients.pop(old_name)
                    username = new_name

                    rename_msg = (
                        f"[{get_time()}] *** {old_name} "
                        f"is now known as {new_name} ***"
                    )

                    print(rename_msg)
                    await broadcast(rename_msg)

            # --------------------------------------
            # /quit
            # --------------------------------------
            elif message == "/quit":
                await websocket.send(
                    f"[{get_time()}] Goodbye {username}!"
                )
                break

            # --------------------------------------
            # Unknown command
            # --------------------------------------
            elif message.startswith("/"):
                await websocket.send(
                    f"[{get_time()}] Unknown command. Type /help for commands."
                )

            # --------------------------------------
            # Regular chat message
            # --------------------------------------
            else:
                chat_msg = f"[{get_time()}] {username}: {message}"
                print(chat_msg)
                await broadcast(chat_msg)

    # ==========================================
    # CONNECTION CLOSED
    # ==========================================
    except websockets.exceptions.ConnectionClosed:
        pass

    # ==========================================
    # CLEANUP ON DISCONNECT
    # ==========================================
    finally:
        if username and username in connected_clients:
            del connected_clients[username]

            leave_msg = (
                f"[{get_time()}] *** {username} has left the chat ***"
            )

            print(leave_msg)
            await broadcast(leave_msg)

async def main():
   print("Pychat server started on ws://localhost:8765")
   print("Waiting for users to connect...\n")
   async with websockets.serve(handler,"localhost", 8765):
       await asyncio.Future()

       
asyncio.run(main())



