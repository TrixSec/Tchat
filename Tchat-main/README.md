# TermChat v2 — Modern Terminal Communication Platform

TermChat v2 is a self-hostable, database-free, lightweight terminal-based chat platform built on Python and WebSockets. It features rich formatting, bidirectionally bridged Telegram notifications, presence statuses, local history logging, and file transfers over WebSocket.

---

## 1. Project Directory Structure

The project conforms to the following layout:
```txt
termchat/
├── server/
│   ├── server.py       # Main WebSocket Broker, assigns message IDs, tracks heartbeats
│   ├── presence.py     # Presence Manager (online, idle, custom status formatting)
│   ├── relay.py        # Telegram Bot Updates Poller & Offline Notifications
│   └── files.py        # File Transfer Offer and Coordination Manager
│
├── client/
│   ├── client.py       # Main Executable client, UI loop, keyboard listener, reconnector
│   ├── ui.py           # ANSI colored terminal outputs and theme templates
│   ├── history.py      # SQLite db manager (~/.termchat/history.db)
│   ├── autocomplete.py # Tab Autocomplete for commands and user names
│   ├── telegram.py     # Telegram Bot Token verification checks
│   └── config.py       # TOML configuration loader (~/.termchat/config.toml)
│
├── shared/
│   ├── protocol.py     # WebSocket JSON event message types and structures
│   └── models.py       # Shared dataclasses
│
├── requirements.txt    # Library dependencies (websockets, aiohttp)
└── README.md           # Instructions and usage details
```

---

## 2. Installation

Install dependencies locally:
```bash
pip install -r requirements.txt
```

---

## 3. Running TermChat v2

### A. Start the Server
Run the central WebSocket server (default port is `8765`):
```bash
python server/server.py --port 8765
```

### B. Run the Client
Run the client in separate terminal windows to connect users:
```bash
python client/client.py --username Alice --host localhost --port 8765
python client/client.py --username Bob --host localhost --port 8765
```

---

## 4. Slash Commands Reference

Inside the client console, you can run the following slash commands:

| Command | Syntax / Usage | Description |
|---|---|---|
| `/help` | `/help` | Lists available commands from the server |
| `/users` | `/users` | Lists online users and their presence states |
| `/dm` | `/dm <username> <message>` | Sends a private message to a specific user |
| `/reply` | `/reply <msg_id> <message>` | Replies to a specific message ID in the thread |
| `/status` | `/status <online\|idle\|busy\|coding\|away>` | Updates user presence status and custom display text |
| `/send` | `/send [username] <filepath>` | Transfers a local file (public or to a DM user) |
| `/theme` | `/theme <dark\|hacker\|dracula\|nord>` | Updates the ANSI terminal styling scheme |
| `/history` | `/history` | Displays the last 20 messages from local database |
| `/search` | `/search <query>` | Searches local history for message content matching `<query>` |
| `/clear` | `/clear` | Clears the terminal screen |
| `/quit` | `/quit` | Cleanly disconnects and exits TermChat |

---

## 5. Rich UI Themes

You can change terminal UI colors using `/theme <name>`. Four themes are supported:
1. `dark` — Sleek, modern dark-grey scheme (Default)
2. `hacker` — Nostalgic green matrix terminal format
3. `dracula` — Purplish palette mapping Dracula colors
4. `nord` — Blue frost arctic aesthetic

---

## 6. File Sharing Over WebSocket

Files are sent chunk-by-chunk over the active WebSocket channel in a database-free manner.

1. **Offer a File**:
   Run `/send README.md` to offer a file to everyone, or `/send Bob README.md` to offer it to Bob privately.
2. **Accept a File**:
   The recipient will see:
   `Bob offered file: README.md (14321 bytes). Accept file? (y/n) >`
3. **Transmission**:
   Typing `y` starts the transfer. Upload/download progress percentages are displayed in real-time. Files are saved in the recipient's current working directory.

---

## 7. Telegram Bot Integration & Bridge

Each user can link a Telegram bot to their account so they can receive offline notifications and reply to terminal chat from mobile.

### Configuration
Update your configuration at `~/.termchat/config.toml`:
```toml
username = "Alice"
theme = "dark"
server_address = "ws://localhost:8765"

[telegram]
bot_token = "YOUR_TELEGRAM_BOT_TOKEN"
chat_id = "YOUR_TELEGRAM_CHAT_ID"

[notifications]
mentions_only = true
```

*Create a Bot by talking to `@BotFather` on Telegram, then fetch your Chat ID using `@userinfobot`.*

### Bidirectional Flows
1. **Offline Notifications**: When Alice is offline and another user mentions Alice (`@Alice`) or sends Alice a DM (`/dm Alice <msg>`), the TermChat server automatically sends a push notification to Alice's Telegram.
2. **Telegram-to-Terminal Relay**: When Alice receives a message on Telegram, replying to her bot forwards the text back into the terminal chat. It will appear on everyone's screens as:
   `[Telegram] Alice: Hello from mobile!`
