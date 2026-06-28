# shared/models.py
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class Message:
    type: str
    id: Optional[int] = None
    user: str = "Unknown"
    content: str = ""
    time: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "id": self.id,
            "user": self.user,
            "content": self.content,
            "time": self.time,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Message':
        return cls(
            type=data.get("type", "chat"),
            id=data.get("id"),
            user=data.get("user", "Unknown"),
            content=data.get("content", ""),
            time=data.get("time", ""),
            metadata=data.get("metadata", {})
        )
