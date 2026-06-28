# shared/protocol.py

import json
from datetime import datetime
from shared.models import Message

def get_time():
    return datetime.now().strftime("%H:%M:%S")

def create_message(
    msg_type: str,
    user: str,
    content: str,
    msg_id: int = None,
    extra: dict = None
):
    """
    Creates a standard TermChat message format.
    """
    msg = Message(
        type=msg_type,
        id=msg_id,
        user=user,
        content=content,
        time=get_time(),
        metadata=extra or {}
    )
    return json.dumps(msg.to_dict())

def parse_message(data: str) -> Message:
    """
    Converts received JSON message into Message object.
    """
    try:
        data_dict = json.loads(data)
        return Message.from_dict(data_dict)
    except json.JSONDecodeError:
        return Message(
            type="error",
            content="Invalid message format"
        )