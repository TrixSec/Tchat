# server/presence.py

class PresenceManager:
    VALID_STATUSES = {"Online", "Idle", "Offline", "Busy", "Coding", "Away"}

    def __init__(self):
        self.statuses = {}

    def set_status(self, username: str, status: str) -> bool:
        status_formatted = status.capitalize()
        if status_formatted in self.VALID_STATUSES:
            self.statuses[username] = status_formatted
            return True
        return False

    def get_status(self, username: str) -> str:
        return self.statuses.get(username, "Offline")

    def remove_user(self, username: str):
        if username in self.statuses:
            del self.statuses[username]
