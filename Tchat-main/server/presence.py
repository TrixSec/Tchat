class PresenceManager:
    def __init__(self):
        # Maps username -> { "status": "online"|"idle"|"offline", "message": str }
        self.presences = {}

    def update_presence(self, username, status, message=""):
        """Updates the status and custom status message of a user."""
        status = status.lower()
        if status not in ["online", "idle", "offline", "busy", "coding", "away"]:
            # If it's a custom status command like /status coding, map status to online
            # and set message to coding.
            if status in ["busy", "coding", "away"]:
                message = status.capitalize()
                status = "online"
            else:
                status = "online"
                
        self.presences[username] = {
            "status": status,
            "message": message
        }

    def remove_user(self, username):
        """Sets the user status to offline."""
        if username in self.presences:
            self.presences[username]["status"] = "offline"

    def get_user_status(self, username):
        """Returns status dictionary for a user."""
        return self.presences.get(username, {"status": "offline", "message": ""})

    def get_online_users_summary(self):
        """Returns a string listing all online/idle users and their custom statuses."""
        online_list = []
        for user, info in self.presences.items():
            status = info["status"]
            if status == "offline":
                continue
                
            dot = "●" if status == "online" else "◐"
            msg_part = f" ({info['message']})" if info["message"] else ""
            online_list.append(f"{user} {dot}{msg_part}")
            
        return ", ".join(online_list) if online_list else "None"
        
    def get_all_presences(self):
        """Returns the full presences dictionary."""
        return self.presences
