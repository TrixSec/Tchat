# client/ui.py

import hashlib
from datetime import datetime
from typing import Dict

from rich.console import Console
from rich.text import Text

from shared.models import Message
from client.themes import theme_manager

console = Console()

def get_time() -> str:
    return datetime.now().strftime("%H:%M:%S")

def get_color_for_user(username: str) -> str:
    # Generate a consistent color based on username hash
    colors = theme_manager.get_user_colors()
    hash_val = int(hashlib.md5(username.encode()).hexdigest(), 16)
    return colors[hash_val % len(colors)]

message_cache: Dict[int, Message] = {}

def format_message(msg_data: dict) -> Text:
    """
    Formats incoming TermChat messages using Rich.
    """
    msg = Message.from_dict(msg_data)
    
    text = Text()
    
    if msg.type == "chat":
        msg_id_val = msg.id
        if msg_id_val is not None:
            message_cache[msg_id_val] = msg
            
        msg_id = msg_id_val if msg_id_val is not None else "?"
        user = msg.user
        content = msg.content
        time_str = msg.time if msg.time else get_time()
        
        user_color = get_color_for_user(user)
        
        dim_style = theme_manager.get_style("dim")
        time_style = theme_manager.get_style("time")
        
        reply_to_id = msg.metadata.get("reply_to") if msg.metadata else None
        if reply_to_id is not None:
            parent_msg = message_cache.get(int(reply_to_id))
            if parent_msg:
                parent_color = get_color_for_user(parent_msg.user)
                text.append("┌─ ", style=dim_style)
                text.append(f"{parent_msg.user}: ", style=f"{parent_color}")
                text.append(f"{parent_msg.content}\n", style=f"{dim_style} italic")
                text.append("└─ ", style=dim_style)
            else:
                text.append("┌─ ", style=dim_style)
                text.append(f"Replied to [{reply_to_id}]\n", style=f"{dim_style} italic")
                text.append("└─ ", style=dim_style)
        
        text.append(f"[{msg_id}] ", style=dim_style)
        text.append(f"[{time_str}] ", style=time_style)
        text.append(f"{user}: ", style=f"bold {user_color}")
        
        # Check if this is a DM
        if msg.metadata and msg.metadata.get("is_dm"):
            text.append(content, style=theme_manager.get_style("dm_message"))
        else:
            text.append(content, style=theme_manager.get_style("message"))
        
    elif msg.type == "system":
        text.append(f"[*] {msg.content}", style=theme_manager.get_style("system"))
        
    elif msg.type == "presence":
        user_color = get_color_for_user(msg.user)
        status = msg.content
        icon = "◐" if status.lower() == "idle" else "●"
        text.append(f"{msg.user} ", style=f"bold {user_color}")
        text.append(f"{icon} {status}", style=theme_manager.get_style("status"))
        
    elif msg.type == "error":
        text.append(f"[ERROR] {msg.content}", style=theme_manager.get_style("error"))
        
    else:
        text.append(str(msg_data))
        
    return text

def print_message(msg_data: dict) -> None:
    text = format_message(msg_data)
    console.print(text)