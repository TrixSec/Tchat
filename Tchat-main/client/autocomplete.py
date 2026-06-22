COMMANDS = [
    "/help", "/users", "/dm", "/reply", "/status", 
    "/history", "/search", "/send", "/theme", "/clear", "/quit"
]

THEMES = ["dark", "hacker", "dracula", "nord"]
STATUS_STATES = ["online", "idle", "busy", "coding", "away"]

def autocomplete(text, online_users=None):
    """
    Given the current input text, tries to autocomplete commands, themes, status, or usernames.
    Returns the completed text string.
    """
    if online_users is None:
        online_users = []
        
    if not text.startswith("/"):
        return text

    parts = text.split(" ")
    
    # 1. Complete the main command (e.g. /us -> /users)
    if len(parts) == 1:
        cmd_part = parts[0]
        matches = [c for c in COMMANDS if c.startswith(cmd_part)]
        if len(matches) == 1:
            return matches[0] + " "
        elif len(matches) > 1:
            # Return the first match for cycling or prefix
            return matches[0] + " "
            
    # 2. Complete arguments for specific commands
    elif len(parts) == 2:
        cmd, arg = parts[0], parts[1]
        
        # Complete username for /dm
        if cmd == "/dm":
            matches = [u for u in online_users if u.lower().startswith(arg.lower())]
            if len(matches) == 1:
                return f"/dm {matches[0]} "
            elif len(matches) > 1:
                return f"/dm {matches[0]} "
                
        # Complete theme names for /theme
        elif cmd == "/theme":
            matches = [t for t in THEMES if t.lower().startswith(arg.lower())]
            if len(matches) == 1:
                return f"/theme {matches[0]} "
            elif len(matches) > 1:
                return f"/theme {matches[0]} "
                
        # Complete presence/status states for /status
        elif cmd == "/status":
            matches = [s for s in STATUS_STATES if s.lower().startswith(arg.lower())]
            if len(matches) == 1:
                return f"/status {matches[0]} "
            elif len(matches) > 1:
                return f"/status {matches[0]} "
                
    return text
