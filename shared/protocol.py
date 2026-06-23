import json
from datetime import datetime

# Message types
MSG_CHAT = "chat"
MSG_DM = "dm"
MSG_REPLY = "reply"
MSG_PRESENCE = "presence"
MSG_FILE_OFFER = "file_offer"
MSG_FILE_ACCEPT = "file_accept"
MSG_FILE_REJECT = "file_reject"
MSG_FILE_CHUNK = "file_chunk"
MSG_FILE_END = "file_end"
MSG_FILE_CANCEL = "file_cancel"
MSG_HEARTBEAT = "heartbeat"
MSG_SYSTEM = "system"
MSG_ERROR = "error"

def get_timestamp():
    return datetime.now().strftime("%H:%M:%S")

def make_message(msg_type, sender, content="", target=None, reply_to=None, file_id=None, extra=None, msg_id=None):
    """
    Constructs a standard message dictionary.
    """
    msg = {
        "id": msg_id,
        "type": msg_type,
        "sender": sender,
        "content": content,
        "target": target,
        "reply_to": reply_to,
        "file_id": file_id,
        "timestamp": get_timestamp(),
        "extra": extra
    }
    return msg

def serialize_message(msg):
    return json.dumps(msg)

def deserialize_message(raw_msg):
    return json.loads(raw_msg)
