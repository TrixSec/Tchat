import asyncio
import sqlite3
import os
import base64
import aiofiles
import websockets
import aiohttp
from datetime import datetime
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog
from textual.containers import Vertical

# ==========================================
# TELEGRAM CONFIG
# ==========================================

BOT_TOKEN = "8859384964:AAEzPkc6D-UYeM1YRoP7fCmNbnJpbwU76zo"
CHAT_ID   = 8550654321


# ==========================================
# COLOR MAP
# ==========================================

USER_COLORS = [
    "bright_cyan", "bright_green", "bright_yellow",
    "bright_magenta", "bright_red", "bright_blue",
    "cyan", "green",
]

user_color_map = {}
color_index    = [0]

def get_user_color(username):
    if username not in user_color_map:
        color = USER_COLORS[color_index[0] % len(USER_COLORS)]
        user_color_map[username] = color
        color_index[0] += 1
    return user_color_map[username]


# ==========================================
# AUTOCOMPLETE
# ==========================================

COMMANDS = [
    "/help", "/users", "/dm", "/reply", "/rpm",
    "/status", "/nick", "/tg", "/send", "/history",
    "/search", "/clear", "/theme", "/quit"
]

THEMES = ["dark", "hacker", "nord", "dracula"]

STATUS_OPTIONS = ["online", "idle", "busy", "away"]

def autocomplete(text: str, online_users: list):
    # Completes commands and usernames
    text = text.strip()

    if not text.startswith("/"):
        return text

    parts = text.split(" ")

    # Complete command name
    if len(parts) == 1:
        matches = [c for c in COMMANDS if c.startswith(text)]
        return matches[0] if matches else text

    command = parts[0]

    # Complete username after /dm, /rpm, /reply, /send
    if command in ["/dm", "/send"] and len(parts) == 2:
        partial = parts[1]
        matches = [u for u in online_users if u.lower().startswith(partial.lower())]
        if matches:
            return f"{command} {matches[0]}"

    # Complete theme name
    if command == "/theme" and len(parts) == 2:
        partial = parts[1]
        matches = [t for t in THEMES if t.startswith(partial)]
        if matches:
            return f"/theme {matches[0]}"

    # Complete status
    if command == "/status" and len(parts) == 2:
        partial = parts[1]
        matches = [s for s in STATUS_OPTIONS if s.startswith(partial)]
        if matches:
            return f"/status {matches[0]}"

    return text


# ==========================================
# THEMES
# ==========================================

THEME_STYLES = {
    "dark": {
        "bg":         "#0d1117",
        "border":     "#30363d",
        "input_bg":   "#161b22",
        "input_border": "#238636",
        "focus_border": "#58a6ff",
        "header_bg":  "#161b22",
        "header_fg":  "#58a6ff",
        "footer_bg":  "#161b22",
        "footer_fg":  "#8b949e",
    },
    "hacker": {
        "bg":         "#000000",
        "border":     "#00ff00",
        "input_bg":   "#001100",
        "input_border": "#00aa00",
        "focus_border": "#00ff00",
        "header_bg":  "#001100",
        "header_fg":  "#00ff00",
        "footer_bg":  "#001100",
        "footer_fg":  "#008800",
    },
    "nord": {
        "bg":         "#2e3440",
        "border":     "#4c566a",
        "input_bg":   "#3b4252",
        "input_border": "#5e81ac",
        "focus_border": "#88c0d0",
        "header_bg":  "#3b4252",
        "header_fg":  "#88c0d0",
        "footer_bg":  "#3b4252",
        "footer_fg":  "#4c566a",
    },
    "dracula": {
        "bg":         "#282a36",
        "border":     "#44475a",
        "input_bg":   "#1e1f29",
        "input_border": "#bd93f9",
        "focus_border": "#ff79c6",
        "header_bg":  "#1e1f29",
        "header_fg":  "#bd93f9",
        "footer_bg":  "#1e1f29",
        "footer_fg":  "#6272a4",
    },
}

def build_css(theme: str) -> str:
    t = THEME_STYLES.get(theme, THEME_STYLES["dark"])
    return f"""
    Screen {{ background: {t["bg"]}; }}

    #chat_log {{
        border: solid {t["border"]};
        background: {t["bg"]};
        height: 1fr;
        padding: 0 1;
    }}

    #input_box {{
        border: solid {t["input_border"]};
        background: {t["input_bg"]};
        height: 3;
        padding: 0 1;
        color: #e6edf3;
    }}

    #input_box:focus {{ border: solid {t["focus_border"]}; }}

    Header {{ background: {t["header_bg"]}; color: {t["header_fg"]}; height: 1; }}
    Footer {{ background: {t["footer_bg"]}; color: {t["footer_fg"]}; height: 1; }}
    """


# ==========================================
# HISTORY DATABASE
# ==========================================

HISTORY_DIR = os.path.join(os.path.expanduser("~"), ".termchat")
HISTORY_DB  = os.path.join(HISTORY_DIR, "history.db")


def setup_database():
    os.makedirs(HISTORY_DIR, exist_ok=True)
    conn = sqlite3.connect(HISTORY_DB)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            message   TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_message(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = sqlite3.connect(HISTORY_DB)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (timestamp, message) VALUES (?, ?)",
        (timestamp, message)
    )
    conn.commit()
    conn.close()


def get_history(limit=50):
    conn = sqlite3.connect(HISTORY_DB)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT timestamp, message FROM messages ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()[::-1]
    conn.close()
    return rows


def search_history(keyword: str):
    conn = sqlite3.connect(HISTORY_DB)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT timestamp, message FROM messages WHERE message LIKE ? ORDER BY id DESC LIMIT 50",
        (f"%{keyword}%",)
    )
    rows = cursor.fetchall()[::-1]
    conn.close()
    return rows


# ==========================================
# TELEGRAM FUNCTIONS
# ==========================================

async def send_telegram(text: str):
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data={
                "chat_id": CHAT_ID,
                "text": text
            }) as response:
                data = await response.json()
                return data.get("ok", False)
    except:
        return False


async def get_telegram_updates(offset: int):
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        return [], offset
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={
                "offset": offset,
                "timeout": 5
            }) as response:
                data     = await response.json()
                updates  = data.get("result", [])
                messages = []
                for update in updates:
                    offset  = update["update_id"] + 1
                    msg     = update.get("message", {})
                    text    = msg.get("text", "")
                    sender  = msg.get("from", {}).get("first_name", "Telegram")
                    if text:
                        messages.append((sender, text))
                return messages, offset
    except:
        return [], offset


# ==========================================
# FILE FUNCTIONS
# ==========================================

async def read_file(filepath: str):
    try:
        async with aiofiles.open(filepath, "rb") as f:
            data    = await f.read()
            encoded = base64.b64encode(data).decode("utf-8")
            return encoded, len(data)
    except:
        return None, 0


async def save_file(filename: str, filedata: str):
    try:
        downloads = os.path.join(
            os.path.expanduser("~"), "Downloads", "termchat"
        )
        os.makedirs(downloads, exist_ok=True)
        filepath = os.path.join(downloads, filename)
        data     = base64.b64decode(filedata)
        async with aiofiles.open(filepath, "wb") as f:
            await f.write(data)
        return filepath
    except:
        return None


# ==========================================
# MAIN APP CLASS
# ==========================================

class TermChatApp(App):

    TITLE = "TermChat v2"

    BINDINGS = [
        ("ctrl+q",  "quit",        "Quit"),
        ("tab",     "autocomplete","Tab Complete"),
    ]

    CSS = build_css("dark")

    def __init__(self, username, websocket):
        super().__init__()
        self.username         = username
        self.websocket        = websocket
        self.telegram_offset  = 0
        self.message_queue    = []
        self.connected        = True
        self.online_users     = []
        self.active_theme     = "dark"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            RichLog(id="chat_log", wrap=True, highlight=True, markup=True),
            Input(placeholder="  Type a message... (/help for commands)", id="input_box"),
        )
        yield Footer()

    async def on_mount(self):
        self.query_one("#input_box", Input).focus()
        asyncio.create_task(self.receive_messages())
        asyncio.create_task(self.poll_telegram())
        asyncio.create_task(self.heartbeat())

        log = self.query_one("#chat_log", RichLog)
        log.write("[bold #58a6ff]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]")
        log.write("[bold #58a6ff]   Welcome to TermChat v2[/]")
        log.write(f"[#8b949e]   Logged in as [bold #e6edf3]{self.username}[/][/]")
        log.write("[#8b949e]   Type [bold]/help[/] to see all commands[/]")
        log.write("[#8b949e]   Press [bold]Tab[/] to autocomplete commands[/]")
        log.write("[bold #58a6ff]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]")

    # ==========================================
    # TAB AUTOCOMPLETE
    # ==========================================

    async def action_autocomplete(self):
        input_box = self.query_one("#input_box", Input)
        current   = input_box.value
        completed = autocomplete(current, self.online_users)
        input_box.value  = completed
        input_box.cursor_position = len(completed)

    # ==========================================
    # RECEIVE MESSAGES
    # ==========================================

    async def receive_messages(self):
        try:
            async for message in self.websocket:
                if isinstance(message, bytes):
                    message = message.decode("utf-8", errors="ignore")
                elif not isinstance(message, str):
                    continue

                if message == "/pong":
                    self.connected = True
                    continue

                # Track online users from /users response
                if "Online Users:" in message:
                    lines = message.split("\n")
                    self.online_users = []
                    for line in lines[1:]:
                        name = line.strip().split(" ")[-2] if "—" in line else ""
                        if name:
                            self.online_users.append(name)

                if not message.startswith("ERROR:"):
                    save_message(message)
                self.display_message(message)

        except:
            self.connected = False
            log = self.query_one("#chat_log", RichLog)
            log.write("[bold red]Connection lost. Retrying...[/]")
            await self.reconnect()

    # ==========================================
    # AUTO RECONNECT
    # ==========================================

    async def reconnect(self):
        log = self.query_one("#chat_log", RichLog)

        for attempt in range(1, 6):
            log.write(f"[#8b949e]Attempt {attempt}/5...[/]")
            await asyncio.sleep(3)

            try:
                new_socket = await websockets.connect("ws://localhost:8765")
                await new_socket.send(self.username)
                response = await new_socket.recv()

                if response == "OK":
                    self.websocket = new_socket
                    self.connected = True

                    log.write("[bold green]Reconnected ✓[/]")

                    # Send queued messages
                    if self.message_queue:
                        log.write(f"[#8b949e]Sending {len(self.message_queue)} queued messages...[/]")
                        for msg in self.message_queue:
                            await new_socket.send(msg)
                        self.message_queue.clear()

                    asyncio.create_task(self.receive_messages())
                    return

            except:
                log.write(f"[bold red]Attempt {attempt} failed.[/]")

        log.write("[bold red]Could not reconnect. Please restart manually.[/]")

    # ==========================================
    # HEARTBEAT
    # ==========================================

    async def heartbeat(self):
        while True:
            await asyncio.sleep(30)
            try:
                await self.websocket.send("/ping")
            except:
                self.connected = False

    # ==========================================
    # POLL TELEGRAM
    # ==========================================

    async def poll_telegram(self):
        if BOT_TOKEN == "8859384964:AAEzPkc6D-UYeM1YRoP7fCmNbnJpbwU76zo":
            return
        while True:
            try:
                messages, self.telegram_offset = await get_telegram_updates(
                    self.telegram_offset
                )
                for sender, text in messages:
                    tg_msg = f"[{datetime.now().strftime('%H:%M')}] [Telegram] {sender}: {text}"
                    save_message(tg_msg)
                    try:
                        await self.websocket.send(f"/tgRelay {sender}: {text}")
                    except:
                        pass
            except:
                pass
            await asyncio.sleep(3)

    # ==========================================
    # DISPLAY MESSAGE
    # ==========================================

    def display_message(self, message: str):
        log = self.query_one("#chat_log", RichLog)

        # Incoming file
        if message.startswith("/incoming "):
            parts    = message.split(" ", 4)
            sender   = parts[1]
            filename = parts[2]
            filesize = parts[3]
            filedata = parts[4]
            log.write(f"[bold #58a6ff]📁 {sender} sent you {filename} ({filesize})[/]")
            log.write(f"[#8b949e]Saving to Downloads/termchat/...[/]")
            asyncio.create_task(self.save_incoming_file(filename, filedata))
            return

        # Reply threads
        if "┌─" in message and "└─" in message:
            lines = message.split("\n")
            for line in lines:
                if "┌─" in line:
                    log.write(f"[#8b949e]{line}[/]")
                elif "└─" in line:
                    log.write(f"[bold #e6edf3]{line}[/]")
                else:
                    log.write(f"[#8b949e]{line}[/]")
            return

        # System messages
        if "***" in message:
            log.write(f"[bold #f0883e]{message}[/]")
            return

        # Errors
        if message.startswith("ERROR:"):
            log.write(f"[bold red]{message}[/]")
            return

        # DM
        if "[DM" in message:
            log.write(f"[bold #bc8cff]{message}[/]")
            return

        # RPM
        if "[RPM" in message:
            lines = message.split("\n")
            for line in lines:
                if "┌─" in line:
                    log.write(f"[#8b949e]{line}[/]")
                elif "└─" in line:
                    log.write(f"[bold #bc8cff]{line}[/]")
                else:
                    log.write(f"[bold #bc8cff]{line}[/]")
            return

        # Telegram
        if "[Telegram]" in message:
            log.write(f"[bold #58a6ff]{message}[/]")
            return

        # History
        if message.startswith("──"):
            log.write(f"[#8b949e]{message}[/]")
            return

        # Regular chat
        try:
            parts = message.split("] ")
            if len(parts) >= 3:
                time_part = parts[0] + "]"
                id_part   = "[" + parts[1] + "]"
                rest      = parts[2]

                if ":" in rest:
                    name, text = rest.split(":", 1)
                    name  = name.strip()
                    color = get_user_color(name)

                    is_mentioned = f"@{self.username}" in text

                    if is_mentioned:
                        text = text.replace(
                            f"@{self.username}",
                            f"[bold yellow]@{self.username}[/bold yellow]"
                        )
                        formatted = (
                            f"[bold yellow]{time_part} {id_part}[/] "
                            f"[bold {color}]{name}[/][#8b949e]:[/] "
                            f"[bold yellow]{text.strip()}[/]"
                        )
                    else:
                        formatted = (
                            f"[#8b949e]{time_part} {id_part}[/] "
                            f"[bold {color}]{name}[/][#8b949e]:[/] "
                            f"[#e6edf3]{text.strip()}[/]"
                        )

                    log.write(formatted)
                    return
        except:
            pass

        log.write(f"[#e6edf3]{message}[/]")

    # ==========================================
    # SAVE INCOMING FILE
    # ==========================================

    async def save_incoming_file(self, filename: str, filedata: str):
        log      = self.query_one("#chat_log", RichLog)
        filepath = await save_file(filename, filedata)
        if filepath:
            log.write(f"[bold green]✓ Saved to: {filepath}[/]")
        else:
            log.write(f"[bold red]✗ Failed to save {filename}[/]")

    # ==========================================
    # SHOW HISTORY
    # ==========================================

    def show_history(self):
        log  = self.query_one("#chat_log", RichLog)
        rows = get_history(50)
        if not rows:
            log.write("[#8b949e]── No history found. ──[/]")
            return
        log.write("[bold #58a6ff]── Chat History (last 50 messages) ──[/]")
        for timestamp, message in rows:
            log.write(f"[#8b949e]{message}[/]")
        log.write("[bold #58a6ff]── End of History ──[/]")

    # ==========================================
    # SHOW SEARCH
    # ==========================================

    def show_search(self, keyword: str):
        log  = self.query_one("#chat_log", RichLog)
        rows = search_history(keyword)
        if not rows:
            log.write(f"[#8b949e]── No messages found containing '{keyword}' ──[/]")
            return
        log.write(f"[bold #58a6ff]── Search results for '{keyword}' ──[/]")
        for timestamp, message in rows:
            highlighted = message.replace(
                keyword,
                f"[bold yellow]{keyword}[/bold yellow]"
            )
            log.write(f"[#8b949e]{highlighted}[/]")
        log.write("[bold #58a6ff]── End of Results ──[/]")

    # ==========================================
    # CHANGE THEME
    # ==========================================

    def change_theme(self, theme: str):
        log = self.query_one("#chat_log", RichLog)
        if theme not in THEME_STYLES:
            log.write(f"[bold red]Unknown theme. Options: dark, hacker, nord, dracula[/]")
            return
        self.active_theme = theme
        type(self).CSS = build_css(theme)
        self.refresh_css()
        log.write(f"[bold #58a6ff]Theme changed to: {theme}[/]")

    # ==========================================
    # ON INPUT SUBMITTED
    # ==========================================

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        message = event.value.strip()
        if not message:
            return

        self.query_one("#input_box", Input).value = ""
        log = self.query_one("#chat_log", RichLog)

        # /history
        if message == "/history":
            self.show_history()
            return

        # /search
        if message.startswith("/search "):
            keyword = message.split(" ", 1)[1].strip()
            if keyword:
                self.show_search(keyword)
            else:
                log.write("[#8b949e]Usage: /search keyword[/]")
            return

        # /clear
        if message == "/clear":
            log.clear()
            return

        # /theme
        if message.startswith("/theme "):
            theme = message.split(" ", 1)[1].strip()
            self.change_theme(theme)
            return

        # /tg
        if message.startswith("/tg "):
            parts = message.split(" ", 1)
            if len(parts) < 2 or not parts[1].strip():
                log.write("[#8b949e]Usage: /tg your message[/]")
                return
            success = await send_telegram(
                f"[TermChat] {self.username}: {parts[1].strip()}"
            )
            if success:
                log.write("[bold #58a6ff][Telegram] Message delivered. ✓[/]")
            else:
                log.write("[bold red][Telegram] Delivery failed.[/]")
            return

        # /send
        if message.startswith("/send "):
            parts = message.split(" ", 2)
            if len(parts) < 3:
                log.write("[#8b949e]Usage: /send username filepath[/]")
                return

            target   = parts[1]
            filepath = parts[2].strip()

            # Check local project folder too
            if not os.path.exists(filepath):
                local_path = os.path.join(os.path.dirname(__file__), filepath)
                if os.path.exists(local_path):
                    filepath = local_path
                else:
                    log.write(f"[bold red]File not found: {filepath}[/]")
                    log.write(f"[#8b949e]Tip: Put file in TermsChat folder and use just the filename[/]")
                    return

            # Check file size limit 10MB
            filesize_bytes = os.path.getsize(filepath)
            if filesize_bytes > 10 * 1024 * 1024:
                log.write("[bold red]File too large. Maximum size is 10 MB.[/]")
                return

            log.write(f"[#8b949e]Reading file...[/]")
            filedata, filesize = await read_file(filepath)

            if not filedata:
                log.write("[bold red]Could not read file.[/]")
                return

            filename = os.path.basename(filepath)
            size_kb  = round(filesize / 1024, 2)

            log.write(f"[#8b949e]Sending {filename} ({size_kb} KB) to {target}...[/]")

            try:
                await self.websocket.send(
                    f"/send {target} {filename} {size_kb}KB {filedata}"
                )
            except:
                log.write("[bold red]Failed to send file.[/]")
            return

        # /quit
        if message == "/quit":
            try:
                await self.websocket.send("/quit")
            except:
                pass
            self.exit()
            return

        # Everything else
        try:
            if not message.startswith("/"):
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                save_message(f"[{timestamp}] {self.username}: {message}")

            if self.connected:
                await self.websocket.send(message)
            else:
                self.message_queue.append(message)
                log.write(f"[#8b949e]Queued: {message}[/]")
        except:
            self.message_queue.append(message)
            log.write(f"[#8b949e]Queued: {message}[/]")

    async def action_quit(self):
        try:
            await self.websocket.send("/quit")
        except:
            pass
        self.exit()


# ==========================================
# STARTUP
# ==========================================

async def start():
    setup_database()

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("       TermChat v2")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    try:
        async with websockets.connect("ws://localhost:8765") as websocket:
            while True:
                username = input("Enter username: ").strip()
                if not username:
                    print("Username cannot be empty.")
                    continue

                await websocket.send(username)
                response = await websocket.recv()

                if response == "OK":
                    print(f"Logged in as {username}. Loading chat...\n")
                    break
                else:
                    print(response)

            app = TermChatApp(username=username, websocket=websocket)
            await app.run_async()

    except ConnectionRefusedError:
        print("\nCould not connect to server.")
        print("Make sure server1.py is running first.")


asyncio.run(start())