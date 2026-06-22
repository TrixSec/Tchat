from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class UserPresence:
    username: str
    status: str = "online"  # "online", "idle", "offline"
    message: str = ""       # Custom status text (e.g. "Coding", "Away")

@dataclass
class FileTransferState:
    file_id: str
    filename: str
    filesize: int
    sender: str
    recipient: Optional[str] = None
    chunks_received: int = 0
    total_chunks: int = 0
    file_pointer: Any = None
    is_sender: bool = False
    cancelled: bool = False
