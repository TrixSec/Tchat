import os
import platform

class ThemeManager:
    def __init__(self):
        self.themes = {
            "dark": {
                "user_colors": [
                    "red", "green", "yellow", "blue", "magenta", "cyan", 
                    "bright_red", "bright_green", "bright_yellow", 
                    "bright_blue", "bright_magenta", "bright_cyan"
                ],
                "message": "",
                "dm_message": "italic magenta",
                "system": "italic yellow",
                "status": "dim",
                "time": "dim cyan",
                "dim": "dim",
                "error": "bold red"
            },
            "hacker": {
                "user_colors": ["bright_green", "green"],
                "message": "green",
                "dm_message": "italic bright_green",
                "system": "bright_green",
                "status": "green",
                "time": "green",
                "dim": "green",
                "error": "bold bright_green"
            },
            "dracula": {
                "user_colors": ["#ff79c6", "#bd93f9", "#8be9fd", "#50fa7b", "#f1fa8c", "#ffb86c"],
                "message": "#f8f8f2",
                "dm_message": "italic #bd93f9",
                "system": "italic #8be9fd",
                "status": "#6272a4",
                "time": "#6272a4",
                "dim": "#6272a4",
                "error": "bold #ff5555"
            },
            "nord": {
                "user_colors": ["#88C0D0", "#81A1C1", "#5E81AC", "#A3BE8C", "#EBCB8B", "#D08770", "#BF616A", "#B48EAD"],
                "message": "#D8DEE9",
                "dm_message": "italic #88C0D0",
                "system": "italic #EBCB8B",
                "status": "#4C566A",
                "time": "#4C566A",
                "dim": "#4C566A",
                "error": "bold #BF616A"
            }
        }
        self.current_theme = "dark"
        self._load_config()

    def _get_config_path(self):
        if platform.system() == "Windows":
            base_dir = os.path.join(os.environ.get("USERPROFILE", ""), ".termchat")
        else:
            base_dir = os.path.expanduser("~/.termchat")
        
        try:
            os.makedirs(base_dir, exist_ok=True)
        except Exception:
            pass
            
        return os.path.join(base_dir, "config.toml")

    def _load_config(self):
        path = self._get_config_path()
        if not os.path.exists(path):
            self.current_theme = "dark"
            return
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("theme") and "=" in line:
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val in self.themes:
                            self.current_theme = val
                            break
        except Exception:
            self.current_theme = "dark"

    def set_theme(self, theme_name):
        if theme_name in self.themes:
            self.current_theme = theme_name
            self._save_config()
            return True
        return False

    def _save_config(self):
        path = self._get_config_path()
        lines = []
        theme_written = False
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            
            with open(path, "w", encoding="utf-8") as f:
                for line in lines:
                    if line.strip().startswith("theme") and "=" in line:
                        f.write(f'theme = "{self.current_theme}"\n')
                        theme_written = True
                    else:
                        f.write(line)
                
                if not theme_written:
                    f.write(f'theme = "{self.current_theme}"\n')
        except Exception:
            pass

    def get_style(self, key):
        theme = self.themes.get(self.current_theme, self.themes["dark"])
        return theme.get(key, "")

    def get_user_colors(self):
        theme = self.themes.get(self.current_theme, self.themes["dark"])
        return theme.get("user_colors", self.themes["dark"]["user_colors"])

theme_manager = ThemeManager()
