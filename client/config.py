import os
import tomllib

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".termchat")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.toml")

DEFAULT_CONFIG = {
    "username": "",
    "theme": "dark",
    "server_address": "ws://localhost:8765",
    "telegram": {
        "bot_token": "",
        "chat_id": ""
    },
    "notifications": {
        "mentions_only": True
    }
}

def ensure_config_dir():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)

def load_config():
    ensure_config_dir()
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    
    try:
        with open(CONFIG_PATH, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        print(f"Error reading config: {e}. Using defaults.")
        return DEFAULT_CONFIG

def save_config(config):
    ensure_config_dir()
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write(f'username = "{config.get("username", "")}"\n')
            f.write(f'theme = "{config.get("theme", "dark")}"\n')
            f.write(f'server_address = "{config.get("server_address", "ws://localhost:8765")}"\n\n')
            
            tg = config.get("telegram", {})
            f.write("[telegram]\n")
            f.write(f'bot_token = "{tg.get("bot_token", "")}"\n')
            f.write(f'chat_id = "{tg.get("chat_id", "")}"\n\n')
            
            notif = config.get("notifications", {})
            f.write("[notifications]\n")
            f.write(f'mentions_only = {str(notif.get("mentions_only", True)).lower()}\n')
    except Exception as e:
        print(f"Error saving config: {e}")
