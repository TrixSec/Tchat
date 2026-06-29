import asyncio
import aiohttp
import websockets
from datetime import datetime

# ==========================================
# TELEGRAM CONFIG
# ==========================================

TELEGRAM_TOKEN   = "8859384964:AAEzPkc6D-UYeM1YRoP7fCmNbnJpbwU76zo"
TELEGRAM_CHAT_ID = 8550654321
TELEGRAM_ENABLED = True


# ==========================================
# DATA STORAGE
# ==========================================

connected_clients = {}
user_status       = {}
message_log       = {}
message_counter   = [0]
offline_users     = set()


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_time():
    return datetime.now().strftime("%H:%M")


def next_id():
    message_counter[0] += 1
    return message_counter[0]


def status_icon(status):
    icons = {
        "online": "●",
        "idle":   "◐",
        "busy":   "◉",
        "away":   "○",
    }
    return icons.get(status.lower(), "●")


# ==========================================
# TELEGRAM SENDER
# ==========================================

async def send_telegram(text: str):
    if not TELEGRAM_ENABLED:
        return
    if TELEGRAM_TOKEN == "YOUR_BOT_TOKEN_HERE":
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data={
                "chat_id":              TELEGRAM_CHAT_ID,
                "text":                 text,
                "disable_notification": "false"
            }) as response:
                await response.json()
    except Exception as e:
        print(f"[Telegram Error] {e}")


# ==========================================
# BROADCAST
# ==========================================

async def broadcast(message, exclude=None):
    for username, client in list(connected_clients.items()):
        if client != exclude:
            try:
                await client.send(message)
            except:
                pass


# ==========================================
# MENTION DETECTOR
# ==========================================

def find_mentions(message: str):
    mentions = []
    words = message.split()
    for word in words:
        if word.startswith("@"):
            name = word[1:].strip(".,!?")
            if name in connected_clients or name in offline_users:
                mentions.append(name)
    return mentions


# ==========================================
# MAIN HANDLER
# ==========================================

async def handler(websocket):

    username = None

    try:

        # ==========================================
        # USERNAME VALIDATION
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

            await websocket.send("OK")
            break

        # ==========================================
        # REGISTER USER
        # ==========================================

        connected_clients[username] = websocket
        user_status[username]       = "online"
        offline_users.discard(username)

        join_msg = f"[{get_time()}] *** {username} {status_icon('online')} has joined the chat ***"
        print(join_msg)
        await broadcast(join_msg)
        await websocket.send(
            f"[{get_time()}] Welcome {username}! Type /help to see commands."
        )

        await send_telegram(f"🟢 {username} joined TermChat")

        # ==========================================
        # MAIN MESSAGE LOOP
        # ==========================================

        async for message in websocket:
            message = message.strip()

            if not message:
                continue

            # ------------------------------------------
            # /help
            # ------------------------------------------
            if message == "/help":
                help_text = (
                    f"[{get_time()}] Available Commands:\n"
                    "  /users               - See who is online\n"
                    "  /dm user msg         - Send a private message\n"
                    "  /reply ID msg        - Reply to a message publicly\n"
                    "  /rpm ID msg          - Reply privately to message author\n"
                    "  /status STATUS       - Set your status (online/idle/busy/away)\n"
                    "  /nick newname        - Change your username\n"
                    "  /tg message          - Send message to Telegram\n"
                    "  /send username file  - Send a file to a user\n"
                    "  /quit                - Leave the chat"
                )
                await websocket.send(help_text)

            # ------------------------------------------
            # /users
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
            # /status
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
            # /reply
            # ------------------------------------------
            elif message.startswith("/reply "):
                parts = message.split(" ", 2)

                if len(parts) < 3:
                    await websocket.send(f"[{get_time()}] Usage: /reply ID your_message")
                else:
                    try:
                        reply_to_id = int(parts[1])
                        reply_text  = parts[2]

                        if reply_to_id not in message_log:
                            await websocket.send(
                                f"[{get_time()}] Message ID [{reply_to_id}] not found."
                            )
                        else:
                            original      = message_log[reply_to_id]
                            original_user = original["user"]
                            original_text = original["text"]
                            reply_id      = next_id()

                            message_log[reply_id] = {
                                "user": username,
                                "text": reply_text
                            }

                            reply_msg = (
                                f"[{get_time()}] [{reply_id}]\n"
                                f"  ┌─ [{reply_to_id}] {original_user}: {original_text}\n"
                                f"  └─ {username}: {reply_text}"
                            )

                            print(reply_msg)
                            await broadcast(reply_msg)

                    except ValueError:
                        await websocket.send(
                            f"[{get_time()}] Message ID must be a number."
                        )

            # ------------------------------------------
            # /rpm
            # ------------------------------------------
            elif message.startswith("/rpm "):
                parts = message.split(" ", 2)

                if len(parts) < 3:
                    await websocket.send(f"[{get_time()}] Usage: /rpm ID your_message")
                else:
                    try:
                        reply_to_id = int(parts[1])
                        reply_text  = parts[2]

                        if reply_to_id not in message_log:
                            await websocket.send(
                                f"[{get_time()}] Message ID [{reply_to_id}] not found."
                            )
                        else:
                            original      = message_log[reply_to_id]
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
                                rpm_msg = (
                                    f"[{get_time()}] [RPM from {username}]\n"
                                    f"  ┌─ [{reply_to_id}] {original_user}: {original_text}\n"
                                    f"  └─ {username}: {reply_text}"
                                )
                                await connected_clients[original_user].send(rpm_msg)
                                await websocket.send(
                                    f"[{get_time()}] [RPM to {original_user}]\n"
                                    f"  ┌─ [{reply_to_id}] {original_user}: {original_text}\n"
                                    f"  └─ {username}: {reply_text}"
                                )

                                if user_status.get(original_user) in ["idle", "away"]:
                                    await send_telegram(
                                        f"📨 RPM from {username}\n"
                                        f"↩ {original_user}: {original_text}\n"
                                        f"└ {username}: {reply_text}"
                                    )

                    except ValueError:
                        await websocket.send(
                            f"[{get_time()}] ID must be a number."
                        )

            # ------------------------------------------
            # /dm
            # ------------------------------------------
            elif message.startswith("/dm "):
                parts = message.split(" ", 2)

                if len(parts) < 3:
                    await websocket.send(f"[{get_time()}] Usage: /dm username message")
                else:
                    target  = parts[1]
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

                        if user_status.get(target) in ["idle", "away"]:
                            await send_telegram(
                                f"💬 DM from {username} → {target}\n{dm_text}"
                            )

            # ------------------------------------------
            # /nick
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
                    connected_clients[new_name] = connected_clients.pop(old_name)
                    user_status[new_name]       = user_status.pop(old_name)
                    username = new_name

                    rename_msg = (
                        f"[{get_time()}] *** {old_name} is now known as {new_name} ***"
                    )
                    print(rename_msg)
                    await broadcast(rename_msg)

            #/ping -  heartbeaet from cient

            elif message == "/ping":
                await websocket.send("/pong")

            # ------------------------------------------
            # /tgRelay — message coming FROM Telegram
            # ------------------------------------------
            elif message.startswith("/tgRelay "):
                relay_text = message.split(" ", 1)[1].strip()
                relay_msg  = f"[{get_time()}] [Telegram] {relay_text}"
                print(relay_msg)
                await broadcast(relay_msg)

            # ------------------------------------------
            # /send username filename filesize filedata
            # ------------------------------------------
            elif message.startswith("/send "):
                parts = message.split(" ", 4)

                if len(parts) < 5:
                    await websocket.send(
                        f"[{get_time()}] Usage: /send username filename"
                    )
                else:
                    target   = parts[1]
                    filename = parts[2]
                    filesize = parts[3]
                    filedata = parts[4]

                    if target not in connected_clients:
                        await websocket.send(
                            f"[{get_time()}] User '{target}' not found."
                        )
                    elif target == username:
                        await websocket.send(
                            f"[{get_time()}] You cannot send files to yourself."
                        )
                    else:
                        # Forward file to target user
                        await connected_clients[target].send(
                            f"/incoming {username} {filename} {filesize} {filedata}"
                        )
                        await websocket.send(
                            f"[{get_time()}] ✓ File '{filename}' sent to {target}"
                        )

            # ------------------------------------------
            # /quit
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
            # Regular chat message
            # ------------------------------------------
            else:
                msg_id = next_id()

                message_log[msg_id] = {
                    "user": username,
                    "text": message
                }

                chat_msg = f"[{get_time()}] [{msg_id}] {username}: {message}"
                print(chat_msg)
                await broadcast(chat_msg)

                mentions = find_mentions(message)
                for mentioned_user in mentions:
                    if mentioned_user not in connected_clients:
                        await send_telegram(
                            f"🔔 {username} mentioned @{mentioned_user}\n{message}"
                        )
                    elif user_status.get(mentioned_user) in ["idle", "away"]:
                        await send_telegram(
                            f"🔔 {username} mentioned @{mentioned_user} "
                            f"({user_status.get(mentioned_user)})\n{message}"
                        )

    except websockets.exceptions.ConnectionClosed:
        pass

    finally:
        if username and username in connected_clients:
            del connected_clients[username]
            del user_status[username]
            offline_users.add(username)

            leave_msg = f"[{get_time()}] *** {username} has left the chat ***"
            print(leave_msg)
            await broadcast(leave_msg)

            await send_telegram(f"🔴 {username} went offline")


# ==========================================
# START SERVER
# ==========================================

async def main():
    print("TermChat v2 Server")
    print("Running on ws://localhost:8765")
    print(f"Telegram: {'Enabled ✓' if TELEGRAM_ENABLED else 'Disabled'}")
    print("Waiting for users...\n")
    async with websockets.serve(handler, "localhost", 8765):
        await asyncio.Future()


while True:
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped.")
        break
    except Exception as e:
        print(f"Server crashed: {e}")
        print("Restarting in 3 seconds...")
        import time
        time.sleep(3)