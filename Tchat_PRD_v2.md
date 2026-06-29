# Product Requirements Document

## TermChat — Modern Terminal Communication Platform

**Version:** 2.0
**Type:** Intermediate Python Networking Project
**Last Updated:** June 2026

---

# 1. Overview

TermChat v2 is a modern terminal-based communication platform that enables real-time messaging between users through a rich command-line interface.

Unlike v1, which focused on learning WebSockets and basic networking concepts, v2 focuses on usability, reliability, extensibility, and cross-platform communication.

The application supports:

* Real-time terminal chat
* Telegram message relays
* Rich terminal UI
* Message history
* File sharing
* Presence tracking
* Automatic reconnection
* Command autocomplete

TermChat remains self-hostable and database-free.

---

# 2. Goals

* Create a production-quality terminal communication platform
* Provide a modern user experience inside the terminal
* Enable communication beyond the terminal through Telegram integration
* Improve reliability during network interruptions
* Keep user data private through local-first storage
* Remain lightweight and easy to self-host

---

# 3. Design Principles

### Local First

Messages are stored locally on each user's device.

The server does not store chat history.

### Self Hosted

Users should be able to run the entire platform on a small VPS or personal machine.

### Privacy Focused

The server acts only as a message relay.

### Terminal Native

The experience should feel designed specifically for terminal users rather than being a web application squeezed into a terminal.

---

# 4. Architecture

The platform consists of:

### Server

Responsible for:

* Managing active connections
* Routing messages
* Presence tracking
* Telegram relay events
* File transfer coordination

The server does NOT:

* Store chat history
* Store logs
* Persist messages

### Client

Responsible for:

* Rendering UI
* Storing history
* File downloads
* Telegram integration
* Local configuration
* Notifications

---

# 5. Core Features

## 5.1 Real-Time Messaging

Users can communicate through:

* Public chat
* Direct messages
* Replies

Messages are delivered instantly through WebSockets.

Example:

```txt
[10:45] Alice: Hello everyone!
[10:46] Bob: Hi Alice!
```

---

## 5.2 Rich Terminal Interface

The client should provide a visually appealing interface.

Features:

* Colored usernames
* Highlighted mentions
* Status bar
* Better message formatting
* Theme support
* Improved layout

Example:

```txt
╭───────────────────────────────╮
│ TermChat v2      Connected ● │
├───────────────────────────────┤
│ Alice > Hello                │
│ Bob   > Hi                   │
╰───────────────────────────────╯
```

Supported themes:

```bash
/theme dark
/theme hacker
/theme dracula
/theme nord
```

---

## 5.3 Telegram Relay

Users may connect a Telegram bot to their account.

Supported flows:

### Terminal → Telegram

Messages are forwarded to Telegram.

### Telegram → Terminal

Telegram messages appear inside the terminal.

Example:

```txt
[Telegram] Alice: Sent from mobile
```

### Offline Notifications

When a user disconnects:

* Mentions
* Direct messages
* Important notifications

may be forwarded to Telegram.

---

# 6. Reliability Features

## 6.1 Automatic Reconnection

When connection is lost:

```txt
Connection lost.

Retrying...
Attempt 1/5
Attempt 2/5

Connected ✓
```

---

## 6.2 Heartbeat System

Clients and servers exchange heartbeat packets.

Inactive clients are automatically removed.

---

## 6.3 Offline Message Queue

Messages written during disconnect are queued locally.

Example:

```txt
Queued 3 messages.
```

Messages are automatically transmitted after reconnection.

---

## 6.4 Error Recovery

The application should gracefully recover from:

* Temporary network failures
* Unexpected disconnects
* Server restarts
* Telegram API failures
* Invalid commands

---

# 7. Reply System

Every message receives a unique identifier.

Example:

```txt
[143] Alice: Deploy complete
```

Users can reply:

```bash
/reply 143 Nice work!
```

Display:

```txt
┌─ Alice: Deploy complete
└─ Nice work!
```

---

# 8. Presence System

Users may publish their current status.

Available states:

```txt
● Online
◐ Idle
○ Offline
```

Commands:

```bash
/status busy
/status coding
/status away
```

Example:

```txt
Alice     ● Coding
Bob       ◐ Idle
Charlie   ○ Offline
```

---

# 9. Local Message History

Every client stores its own history.

Suggested locations:

```txt
~/.termchat/history.db
```

or

```txt
~/.termchat/logs/
```

The server stores no message history.

Commands:

```bash
/history
/search websocket
```

---

# 10. File Sharing

Users may transfer files directly through the platform.

Command:

```bash
/send README.md
```

Features:

* Transfer progress
* Download confirmation
* File metadata
* Transfer cancellation

Example:

```txt
Alice sent README.md (14 KB)

Accept? (y/n)
```

---

# 11. Command Autocomplete

The terminal should support tab completion.

Example:

```bash
/us<TAB>
```

becomes:

```bash
/users
```

Username completion:

```bash
/dm ali<TAB>
```

becomes:

```bash
/dm alice
```

---

# 12. Commands

| Command  | Description             |
| -------- | ----------------------- |
| /help    | Show available commands |
| /users   | List online users       |
| /dm      | Send direct message     |
| /reply   | Reply to a message      |
| /status  | Update presence         |
| /history | View local history      |
| /search  | Search history          |
| /send    | Transfer file           |
| /theme   | Change theme            |
| /clear   | Clear terminal          |
| /quit    | Exit application        |

---

# 13. Configuration

Configuration is stored locally.

Example location:

```txt
~/.termchat/config.toml
```

Settings include:

* Username
* Theme
* Telegram settings
* Server address
* Notification preferences

---

# 14. Project Structure

```txt
termchat/

├── server/
│   ├── server.py
│   ├── presence.py
│   ├── relay.py
│   └── files.py
│
├── client/
│   ├── client.py
│   ├── ui.py
│   ├── history.py
│   ├── autocomplete.py
│   ├── telegram.py
│   └── config.py
│
├── shared/
│   ├── protocol.py
│   └── models.py
│
├── configs/
│
└── README.md
```

---

# 15. Suggested Milestones

### Phase 1

* Core messaging
* Rich UI
* User colors

### Phase 2

* Presence system
* Reply system
* Message IDs

### Phase 3

* Local history
* Search functionality

### Phase 4

* Telegram bridge

### Phase 5

* File sharing

### Phase 6

* Auto reconnect
* Offline queue
* Heartbeats

### Phase 7

* Command autocomplete
* Final polish

---

# 16. Acceptance Criteria

The project is complete when:

* [ ] Multiple users can chat in real time
* [ ] Telegram relay functions correctly
* [ ] Local message history works
* [ ] Server stores no chat logs
* [ ] Automatic reconnect functions correctly
* [ ] Presence states update correctly
* [ ] File sharing succeeds
* [ ] Reply chains render correctly
* [ ] Command autocomplete works
* [ ] Heartbeat system removes dead connections safely

---

# 17. Vision

TermChat v2 transforms the original learning project into a lightweight communication platform.

It combines:

* IRC-style simplicity
* Discord-inspired usability
* Telegram mobility
* Modern terminal UX

while remaining self-hosted, privacy-focused, and database-free.
