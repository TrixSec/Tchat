import sys
from rich.panel import Panel
from rich.text import Text

class StatusBar:
    def __init__(self):
        self.connected = False
        self.username = ""
        self.theme = ""
        self.unread = 0
        self.is_setup = False
        
    def setup(self):
        sys.stdout.write("\033[2J")     # Clear screen
        sys.stdout.write("\033[4;r")    # Set scroll region: line 4 to bottom
        sys.stdout.write("\033[4;1H")   # Move cursor to line 4
        sys.stdout.flush()
        self.is_setup = True
        self.draw()

    def update(self, connected=None, username=None, theme=None, unread_add=0, unread_clear=False):
        if connected is not None: 
            self.connected = connected
        if username is not None: 
            self.username = username
        if theme is not None: 
            self.theme = theme
            
        if unread_clear:
            self.unread = 0
        else:
            self.unread += unread_add
            
        if self.is_setup:
            self.draw()

    def draw(self):
        if not self.is_setup:
            return
            
        conn_str = "Connected" if self.connected else "Disconnected"
        conn_color = "green" if self.connected else "red"
        
        text = Text()
        text.append(" TeleSync ● ", style="bold cyan")
        text.append(f"{conn_str} ", style=f"bold {conn_color}")
        text.append(f"| User: {self.username} | Theme: {self.theme} | Unread: {self.unread} ")
        
        panel = Panel(text, style="blue")
        
        from client.ui import console
        with console.capture() as cap:
            console.print(panel)
            
        sys.stdout.write("\033[s")       # Save cursor
        sys.stdout.write("\033[1;1H")    # Move to top-left
        sys.stdout.write(cap.get())      # Print the panel
        sys.stdout.write("\033[u")       # Restore cursor
        sys.stdout.flush()

status_bar = StatusBar()
