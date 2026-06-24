import asyncio
import websockets
from datetime import datetime

# ==========================================
# DATA STORAGE
# ==========================================

connected_clients = {}   # username -> websocket
user_status = {}         # username -> status string (e.g. "Online", "Busy")
message_log = {}         # message_id -> {"user": ..., "text": ...}
message_counter = [0]    # using a list so we can modify it inside functions


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_time():
    return datetime.now().strftime("%H:%M")


def next_id():
    # Every message gets a unique number like [1], [2], [3]...
    message_counter[0] += 1
    return message_counter[0]


def status_icon(status):
    # Converts status word into a symbol
    icons = {
        "online": "●",
        "idle":   "◐",
        "busy":   "◉",
        "away":   "○",
    }
    return icons.get(status.lower(), "●")


async def broadcast(message, exclude=None):
    # Sends a message to everyone connected (except the excluded user)
    for username, client in list(connected_clients.items()):
        if client != exclude:
            try:
                await client.send(message)
            except:
                pass


# ==========================================
# MAIN HANDLER — runs once per connected user
# ==========================================

async def handler(websocket):

    username = None

    try:

        # ==========================================
        # STEP 1 — USERNAME VALIDATION
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

            # Username is valid — confirm to client
            await websocket.send("OK")
            break

        # ==========================================
        # STEP 2 — REGISTER USER
        # ==========================================

        connected_clients[username] = websocket
        user_status[username] = "online"   # default status when joining

        join_msg = f"[{get_time()}] *** {username} {status_icon('online')} has joined the chat ***"
        print(join_msg)
        await broadcast(join_msg)

        # Welcome message only to the new user
        await websocket.send(
            f"[{get_time()}] Welcome {username}! Type /help to see commands."
        )

        # ==========================================
        # STEP 3 — MAIN MESSAGE LOOP
        # ==========================================

        async for message in websocket:
            message = message.strip()

            if not message:
                continue

            # ------------------------------------------
            # /help — show all available commands
            # ------------------------------------------
            if message == "/help":
                help_text = (
                    f"[{get_time()}] Available Commands:\n"
                    "  /users             - See who is online\n"
                    "  /dm user msg       - Send a private message\n"
                    "  /reply ID msg      - Reply to a message by its ID publicly\n"
                    "  /rpm ID msg        - Reply to a message by ID privately to author\n"
                    "  /status STATUS     - Set your status (online/idle/busy/away)\n"
                    "  /nick newname      - Change your username\n"
                    "  /quit              - Leave the chat"
                )
                await websocket.send(help_text)

            # ------------------------------------------
            # /users — list everyone online with status
            # ------------------------------------------
            elif message == "/users":
                if not connected_clients:
                    await websocket.send(f"[{get_time()}] Nobody is online.")
                else:
                    lines = [f"[{get_time()}] Online Users:"]
                    for user, status in user_status.items():
                        icon = status_icon(status)
                        lines.append(f"  {icon} {user} — {status.capitalize()}")
                    await websocket.send("\n".join(lines))

            # ------------------------------------------
            # /status — update presence (online/idle/busy/away)
            # ------------------------------------------
            elif message.startswith("/status "):
                new_status = message.split(" ", 1)[1].strip().lower()
                valid_statuses = ["online", "idle", "busy", "away"]

                if new_status not in valid_statuses:
                    await websocket.send(
                        f"[{get_time()}] Valid statuses: online, idle, busy, away"
                    )
                else:
                    user_status[username] = new_status
                    icon = status_icon(new_status)
                    status_msg = f"[{get_time()}] *** {username} is now {icon} {new_status.capitalize()} ***"
                    print(status_msg)
                    await broadcast(status_msg)

            # ------------------------------------------
            # /reply ID message — reply to a specific message
            # ------------------------------------------
            elif message.startswith("/reply "):
                parts = message.split(" ", 2)

                if len(parts) < 3:
                    await websocket.send(
                        f"[{get_time()}] Usage: /reply ID your_message"
                    )
                else:
                    try:
                        reply_to_id = int(parts[1])   # the message ID number
                        reply_text = parts[2]

                        if reply_to_id not in message_log:
                            await websocket.send(
                                f"[{get_time()}] Message ID [{reply_to_id}] not found."
                            )
                        else:
                            # Get the original message details
                            original = message_log[reply_to_id]
                            original_user = original["user"]
                            original_text = original["text"]

                            # Give reply its own ID too
                            reply_id = next_id()

                            # Store the reply in message log
                            message_log[reply_id] = {
                                "user": username,
                                "text": reply_text
                            }

                            # Format: shows original message then reply below it
                            reply_msg = (
                                f"[{get_time()}] [{reply_id}]\n"
                                f"  ┌─ [{reply_to_id}] {original_user}: {original_text}\n"
                                f"  └─ {username}: {reply_text}"
                            )

                            print(reply_msg)
                            await broadcast(reply_msg)

                    except ValueError:
                        await websocket.send(
                            f"[{get_time()}] Message ID must be a number. Usage: /reply 5 your_message"
                        )

            # ------------------------------------------
            # /dm username message — private message
            # ------------------------------------------
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

            # ------------------------------------------
            # /nick newname — change username
            # ------------------------------------------
            elif message.startswith("/nick "):
                new_name = message.split(" ", 1)[1].strip()

                if not new_name:
                    await websocket.send(f"[{get_time()}] Usage: /nick newname")

                elif new_name in connected_clients:
                    await websocket.send(
                        f"[{get_time()}] Username '{new_name}' is already taken."
                    )
                else:
                    old_name = username

                    # Move websocket to new name in both dicts
                    connected_clients[new_name] = connected_clients.pop(old_name)
                    user_status[new_name] = user_status.pop(old_name)
                    username = new_name

                    rename_msg = (
                        f"[{get_time()}] *** {old_name} is now known as {new_name} ***"
                    )
                    print(rename_msg)
                    await broadcast(rename_msg)
            

                        # ------------------------------------------
            # /rpm ID message — private reply to a message
            # ------------------------------------------
            elif message.startswith("/rpm "):
                parts = message.split(" ", 2)

                if len(parts) < 3:
                    await websocket.send(
                        f"[{get_time()}] Usage: /rpm ID your_message"
                    )
                else:
                    try:
                        reply_to_id = int(parts[1])
                        reply_text = parts[2]

                        if reply_to_id not in message_log:
                            await websocket.send(
                                f"[{get_time()}] Message ID [{reply_to_id}] not found."
                            )
                        else:
                            original = message_log[reply_to_id]
                            original_user = original["user"]
                            original_text = original["text"]

                            if original_user not in connected_clients:
                                await websocket.send(
                                    f"[{get_time()}] {original_user} is no longer online."
                                )
                            elif original_user == username:
                                await websocket.send(
                                    f"[{get_time()}] You cannot RPM yourself."
                                )
                            else:
                                await connected_clients[original_user].send(
                                    f"[{get_time()}] [RPM from {username}]\n"
                                    f"  ┌─ [{reply_to_id}] {original_user}: {original_text}\n"
                                    f"  └─ {username}: {reply_text}"
                                )

                                await websocket.send(
                                    f"[{get_time()}] [RPM to {original_user}]\n"
                                    f"  ┌─ [{reply_to_id}] {original_user}: {original_text}\n"
                                    f"  └─ {username}: {reply_text}"
                                )

                    except ValueError:
                        await websocket.send(
                            f"[{get_time()}] ID must be a number. Usage: /rpm 5 your_message"
                        )
            # ------------------------------------------
            # /quit — clean exit
            # ------------------------------------------
            elif message == "/quit":
                await websocket.send(f"[{get_time()}] Goodbye {username}!")
                break

            # ------------------------------------------
            # Unknown command
            # ------------------------------------------
            elif message.startswith("/"):
                await websocket.send(
                    f"[{get_time()}] Unknown command. Type /help for help."
                )

            # ------------------------------------------
            # Regular chat message — gets a unique ID
            # ------------------------------------------
            else:
                msg_id = next_id()

                # Save message so /reply can reference it later
                message_log[msg_id] = {
                    "user": username,
                    "text": message
                }

                chat_msg = f"[{get_time()}] [{msg_id}] {username}: {message}"
                print(chat_msg)
                await broadcast(chat_msg)

    # ==========================================
    # CONNECTION LOST UNEXPECTEDLY
    # ==========================================
    except websockets.exceptions.ConnectionClosed:
        pass

    # ==========================================
    # CLEANUP — runs no matter how user left
    # ==========================================
    finally:
        if username and username in connected_clients:
            del connected_clients[username]
            del user_status[username]

            leave_msg = f"[{get_time()}] *** {username} has left the chat ***"
            print(leave_msg)
            await broadcast(leave_msg)


# ==========================================
# START SERVER
# ==========================================

async def main():
    print("TermChat v2 Server")
    print("Running on ws://localhost:8765")
    print("Waiting for users...\n")
    async with websockets.serve(handler, "localhost", 8765):
        await asyncio.Future()


asyncio.run(main())