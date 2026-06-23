class FileTransferManager:
    def __init__(self):
        # Maps file_id -> { "sender": str, "recipient": str|None, "filename": str, "filesize": int, "accepted": bool }
        self.transfers = {}

    def register_offer(self, file_id, sender, recipient, filename, filesize):
        self.transfers[file_id] = {
            "sender": sender,
            "recipient": recipient, # None means public/broadcast offer
            "filename": filename,
            "filesize": filesize,
            "accepted": False
        }

    def get_transfer(self, file_id):
        return self.transfers.get(file_id)

    def mark_accepted(self, file_id, recipient):
        transfer = self.transfers.get(file_id)
        if transfer:
            # If the transfer is public (recipient is None), we can lock the recipient to the first user who accepts
            if transfer["recipient"] is None:
                transfer["recipient"] = recipient
            if transfer["recipient"] == recipient:
                transfer["accepted"] = True
                return True
        return False

    def remove_transfer(self, file_id):
        if file_id in self.transfers:
            del self.transfers[file_id]
