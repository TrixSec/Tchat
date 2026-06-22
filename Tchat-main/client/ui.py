import os
import sys
import hashlib

# ANSI Color codes
RESET = "\033[0m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"

# Basic Foreground Colors
BLACK = "\033[30m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

# Bright Foreground Colors
BRIGHT_BLACK = "\033[90m"
BRIGHT_RED = "\033[91m"
BRIGHT_GREEN = "\033[92m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_BLUE = "\033[94m"
BRIGHT_MAGENTA = "\033[95m"
BRIGHT_CYAN = "\033[96m"
BRIGHT_WHITE = "\033[97m"

# Background Colors
BG_BLACK = "\033[40m"
BG_RED = "\033[41m"
BG_GREEN = "\033[42m"
BG_YELLOW = "\033[43m"
BG_BLUE = "\033[44m"
BG_MAGENTA = "\033[45m"
BG_CYAN = "\033[46m"
BG_WHITE = "\033[47m"
BG_BRIGHT_BLACK = "\033[100m"

# Enable virtual terminal processing on Windows for ANSI support
if sys.platform == "win32":
    os.system("color")

USER_COLORS = [
    GREEN, YELLOW, BLUE, MAGENTA, CYAN, 
    BRIGHT_GREEN, BRIGHT_YELLOW, BRIGHT_BLUE, BRIGHT_MAGENTA, BRIGHT_CYAN
]

THEMES = {
    "dark": {
        "system": BRIGHT_BLACK,
        "error": BRIGHT_RED,
        "self": BRIGHT_GREEN,
        "dm": BRIGHT_MAGENTA,
        "reply": BRIGHT_YELLOW,
        "timestamp": BRIGHT_BLACK,
        "status_bg": BG_BRIGHT_BLACK,
        "status_fg": BRIGHT_WHITE,
    },
    "hacker": {
        "system": GREEN,
        "error": RED,
        "self": BRIGHT_GREEN + BOLD,
        "dm": GREEN + UNDERLINE,
        "reply": GREEN,
        "timestamp": GREEN,
        "status_bg": BG_BLACK,
        "status_fg": BRIGHT_GREEN,
    },
    "dracula": {
        "system": BRIGHT_CYAN,
        "error": BRIGHT_RED + BOLD,
        "self": BRIGHT_MAGENTA,
        "dm": BRIGHT_CYAN,
        "reply": BRIGHT_YELLOW,
        "timestamp": BRIGHT_BLACK,
        "status_bg": BG_MAGENTA,
        "status_fg": BRIGHT_WHITE,
    },
    "nord": {
        "system": BRIGHT_CYAN,
        "error": RED,
        "self": BRIGHT_BLUE,
        "dm": BRIGHT_MAGENTA,
        "reply": YELLOW,
        "timestamp": BRIGHT_BLACK,
        "status_bg": BG_BLUE,
        "status_fg": BRIGHT_WHITE,
    }
}

class TerminalUI:
    def __init__(self, theme_name="dark"):
        self.theme_name = theme_name if theme_name in THEMES else "dark"
        self.theme = THEMES[self.theme_name]
        self.input_buffer = ""
        self.prompt = "> "
        self.status_line = "TermChat v2 | Disconnected"
        self.is_active = True
        
    def set_theme(self, theme_name):
        if theme_name in THEMES:
            self.theme_name = theme_name
            self.theme = THEMES[theme_name]
            return True
        return False
        
    def get_user_color(self, username):
        """Hashes username to get a consistent colored text styling."""
        if self.theme_name == "hacker":
            return BRIGHT_GREEN
        h = int(hashlib.md5(username.encode("utf-8")).hexdigest(), 16)
        return USER_COLORS[h % len(USER_COLORS)]

    def format_message(self, msg_id, sender, content, msg_type, timestamp, reply_to=None, target=None):
        timestamp_str = f"{self.theme['timestamp']}[{timestamp}]{RESET}"
        id_str = f"{self.theme['system']}[{msg_id}]{RESET} " if msg_id else ""
        
        if msg_type == "system":
            return f"{timestamp_str} {self.theme['system']}*** {content} ***{RESET}"
        elif msg_type == "error":
            return f"{timestamp_str} {self.theme['error']}[ERROR]: {content}{RESET}"
        elif msg_type == "dm":
            if sender == target: # local view self DM
                return f"{timestamp_str} {id_str}{self.theme['dm']}[DM to {target}]: {content}{RESET}"
            return f"{timestamp_str} {id_str}{self.theme['dm']}[DM from {sender}]: {content}{RESET}"
        elif msg_type == "reply":
            reply_header = f"{self.theme['reply']}┌─ Reply to message [{reply_to}]{RESET}\n"
            user_color = self.get_user_color(sender)
            body = f"{timestamp_str} {id_str}└─ {user_color}{sender}{RESET}: {content}"
            return reply_header + body
        else: # chat
            user_color = self.get_user_color(sender)
            return f"{timestamp_str} {id_str}{user_color}{sender}{RESET}: {content}"

    def update_status(self, connected, username=None, presence="online", custom_status="", online_users=None):
        status_dot = "●" if presence == "online" else ("◐" if presence == "idle" else "○")
        presence_color = BRIGHT_GREEN if presence == "online" else (BRIGHT_YELLOW if presence == "idle" else BRIGHT_BLACK)
        
        status_text = f" TermChat v2 "
        if connected:
            user_str = f"| User: {username} {presence_color}{status_dot}{RESET}"
            if custom_status:
                user_str += f" ({custom_status})"
            users_list = f" | Online: {online_users}" if online_users else ""
            status_text += f"● Connected {user_str}{users_list} "
        else:
            status_text += f"○ Disconnected "
            
        # Center or pad status text
        self.status_line = status_text

    def print_text(self, text):
        """Prints text safely without destroying the input line at the bottom."""
        # \r moves cursor to start, \033[K clears from cursor to end of line
        # We move up 2 lines (since status line and input line are at the bottom)
        sys.stdout.write("\r\033[K")
        sys.stdout.write("\033[1A\033[K") # go up 1 line and clear
        sys.stdout.write("\033[1A\033[K") # go up 2nd line and clear
        
        # Print the text
        sys.stdout.write(text + "\n")
        
        # Print status bar & input prompt back
        self.draw_input_area()

    def draw_input_area(self):
        """Draws the status bar and the current input prompt + buffer at the bottom of the terminal."""
        # 1. Print Status Bar
        status_bg = self.theme["status_bg"]
        status_fg = self.theme["status_fg"]
        
        # Terminal width
        try:
            width = os.get_terminal_size().columns
        except OSError:
            width = 80
            
        plain_status = self.status_line.replace(BRIGHT_GREEN, "").replace(BRIGHT_YELLOW, "").replace(BRIGHT_BLACK, "").replace(RESET, "")
        padding = max(0, width - len(plain_status) - 1)
        full_status = f"{status_bg}{status_fg}{self.status_line}{' ' * padding}{RESET}\n"
        
        sys.stdout.write(full_status)
        
        # 2. Print Prompt + Input Buffer
        sys.stdout.write(f"\r\033[K{self.prompt}{self.input_buffer}")
        sys.stdout.flush()

    def handle_character(self, char):
        """Appends character to buffer and draws it."""
        self.input_buffer += char
        sys.stdout.write(char)
        sys.stdout.flush()

    def handle_backspace(self):
        """Removes the last character from buffer."""
        if len(self.input_buffer) > 0:
            self.input_buffer = self.input_buffer[:-1]
            # Move back 1, clear to end of line, rewrite (or just redraw input area)
            sys.stdout.write("\b \b")
            sys.stdout.flush()

    def clear_input(self):
        """Clears the input buffer."""
        self.input_buffer = ""
        # Redraw
        sys.stdout.write("\r\033[K")
        self.draw_input_area()
