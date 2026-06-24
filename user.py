import asyncio
import websockets
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog
from textual.containers import Vertical


# ==========================================
# COLOR MAP — each user gets a unique color
# ==========================================

USER_COLORS = [
    "bright_cyan",
    "bright_green",
    "bright_yellow",
    "bright_magenta",
    "bright_red",
    "bright_blue",
    "cyan",
    "green",
]

user_color_map = {}   # username -> color
color_index = [0]     # tracks which color to assign next

def get_user_color(username):
    # If user already has a color, return it
    # Otherwise assign the next available color
    if username not in user_color_map:
        color = USER_COLORS[color_index[0] % len(USER_COLORS)]
        user_color_map[username] = color
        color_index[0] += 1
    return user_color_map[username]


# ==========================================
# MAIN APP CLASS
# ==========================================

class TermChatApp(App):

    # App title shown in header
    TITLE = "TermChat v2"

    # Keyboard shortcuts shown in footer
    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+c", "quit", "Quit"),
    ]

    # ==========================================
    # CSS — styling for the layout
    # ==========================================

    CSS = """
    Screen {
        background: #0d1117;
    }

    #chat_log {
        border: solid #30363d;
        background: #0d1117;
        height: 1fr;
        padding: 0 1;
        scrollbar-color: #30363d #0d1117;
    }

    #input_box {
        border: solid #238636;
        background: #161b22;
        height: 3;
        padding: 0 1;
        color: #e6edf3;
    }

    #input_box:focus {
        border: solid #58a6ff;
    }

    Header {
        background: #161b22;
        color: #58a6ff;
        height: 1;
    }

    Footer {
        background: #161b22;
        color: #8b949e;
        height: 1;
    }
    """

    def __init__(self, username, websocket):
        super().__init__()
        self.username = username
        self.websocket = websocket

    # ==========================================
    # COMPOSE — builds the visual layout
    # ==========================================

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            RichLog(id="chat_log", wrap=True, highlight=True, markup=True),
            Input(placeholder="  Type a message... (/help for commands)", id="input_box"),
        )
        yield Footer()

    # ==========================================
    # ON MOUNT — runs when app starts
    # ==========================================

    async def on_mount(self):
        # Focus the input box immediately
        self.query_one("#input_box", Input).focus()

        # Start background task to receive messages
        asyncio.create_task(self.receive_messages())

        # Show welcome banner in chat log
        log = self.query_one("#chat_log", RichLog)
        log.write("[bold #58a6ff]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]")
        log.write("[bold #58a6ff]   Welcome to TermChat v2[/]")
        log.write(f"[#8b949e]   Logged in as [bold #e6edf3]{self.username}[/][/]")
        log.write("[#8b949e]   Type [bold]/help[/] to see all commands[/]")
        log.write("[bold #58a6ff]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]")

    # ==========================================
    # RECEIVE MESSAGES — background listener
    # ==========================================

    async def receive_messages(self):
        # Keeps listening for messages from server forever
        try:
            async for message in self.websocket:
                self.display_message(message)
        except:
            # Connection lost
            log = self.query_one("#chat_log", RichLog)
            log.write("[bold red]Connection lost. Please restart.[/]")

    # ==========================================
    # DISPLAY MESSAGE — formats and shows message
    # ==========================================

    def display_message(self, message: str):
        log = self.query_one("#chat_log", RichLog)

        # ------------------------------------------
        # Reply messages (contain ┌─ and └─)
        # ------------------------------------------
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

        # ------------------------------------------
        # System/join/leave messages (contain ***)
        # ------------------------------------------
        if "***" in message:
            log.write(f"[bold #f0883e]{message}[/]")
            return

        # ------------------------------------------
        # Error messages
        # ------------------------------------------
        if message.startswith("ERROR:"):
            log.write(f"[bold red]{message}[/]")
            return

        # ------------------------------------------
        # DM messages
        # ------------------------------------------
        if "[DM" in message:
            log.write(f"[bold #bc8cff]{message}[/]")
            return
        
        # RPM messages — private replies
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


        # ------------------------------------------
        # Telegram messages
        # ------------------------------------------
        if "[Telegram]" in message:
            log.write(f"[bold #58a6ff]{message}[/]")
            return

        # ------------------------------------------
        # Regular chat messages — color the username
        # ------------------------------------------
        # Format is: [HH:MM] [ID] Username: message
        # We extract username and color it
        try:
            # Find the username part after the timestamp and ID
            parts = message.split("] ")
            if len(parts) >= 3:
                # parts[0] = [HH:MM
                # parts[1] = [ID
                # parts[2] = Username: message text
                time_part = parts[0] + "]"
                id_part = "[" + parts[1] + "]"
                rest = parts[2]

                if ":" in rest:
                    name, text = rest.split(":", 1)
                    name = name.strip()
                    color = get_user_color(name)

                    # Highlight mentions of our own username
                    if f"@{self.username}" in text:
                        text = text.replace(
                            f"@{self.username}",
                            f"[bold yellow]@{self.username}[/bold yellow]"
                        )

                    formatted = (
                        f"[#8b949e]{time_part} {id_part}[/] "
                        f"[bold {color}]{name}[/][#8b949e]:[/] "
                        f"[#e6edf3]{text.strip()}[/]"
                    )
                    log.write(formatted)
                    return
        except:
            pass

        # Fallback — just show the message as-is
        log.write(f"[#e6edf3]{message}[/]")

    # ==========================================
    # ON INPUT SUBMITTED — when user presses Enter
    # ==========================================

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        message = event.value.strip()

        if not message:
            return

        # Clear the input box
        self.query_one("#input_box", Input).value = ""

        # Handle /quit locally
        if message == "/quit":
            try:
                await self.websocket.send("/quit")
            except:
                pass
            self.exit()
            return

        # Send everything else to server
        try:
            await self.websocket.send(message)
        except:
            log = self.query_one("#chat_log", RichLog)
            log.write("[bold red]Failed to send. Connection lost.[/]")

    # ==========================================
    # ACTION QUIT — triggered by Ctrl+Q
    # ==========================================

    async def action_quit(self):
        try:
            await self.websocket.send("/quit")
        except:
            pass
        self.exit()


# ==========================================
# STARTUP — username prompt then launch UI
# ==========================================

async def start():

    uri = "ws://localhost:8765"

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("       TermChat v2")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    try:
        async with websockets.connect(uri) as websocket:

            # ==========================================
            # USERNAME LOOP — keep asking until accepted
            # ==========================================
            while True:
                username = input("Enter username: ").strip()

                if not username:
                    print("Username cannot be empty. Try again.")
                    continue

                # Send username to server
                await websocket.send(username)

                # Wait for server response
                response = await websocket.recv()

                if response == "OK":
                    print(f"Logged in as {username}. Loading chat...\n")
                    break
                else:
                    # Server sent an error (username taken, etc.)
                    print(response)
                    continue

            # ==========================================
            # LAUNCH TEXTUAL APP
            # ==========================================
            app = TermChatApp(username=username, websocket=websocket)
            await app.run_async()

    except ConnectionRefusedError:
        print("\nCould not connect to server.")
        print("Make sure server.py is running first.")
        print("Run: python server.py")


# ==========================================
# ENTRY POINT
# ==========================================

asyncio.run(start())