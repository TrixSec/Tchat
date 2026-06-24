import asyncio
from shared.protocol import create_message

async def handle_file_message(msg_type, msg_data, sender_username, clients, get_next_id):
    """
    Relays file transfer messages without storing files on the server.
    msg_type will be one of: file_offer, file_reply, file_chunk, file_cancel
    """
    metadata = msg_data.get("metadata", {})
    
    # Target can be a specific username or empty for broadcast
    target = metadata.get("target")
    
    forward_msg = create_message(
        msg_type, 
        sender_username, 
        msg_data.get("content", ""), 
        msg_id=get_next_id(), 
        extra=metadata
    )
    
    if target and target in clients:
        # Direct route
        await clients[target].send_str(forward_msg)
    else:
        # Broadcast to all except sender
        tasks = [
            ws.send_str(forward_msg) 
            for uname, ws in clients.items() 
            if uname != sender_username
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
