# Product Requirements Document
## TermChat — A Terminal Chat Application

**Version:** 1.0  
**Type:** Beginner Python Assignment  
**Last Updated:** June 2026

---

## 1. Overview

TermChat is a command-line chat application that lets multiple users send and receive messages in real time through a shared terminal interface. Users connect to a central server over WebSockets and can chat with each other, run slash commands, and see who's online.

This is a beginner-level assignment focused on learning Python, networking basics, and real-time communication.

---

## 2. Goals

- Build a working real-time chat app that runs entirely in the terminal
- Learn how WebSockets work for two-way communication
- Practice Python async programming with `asyncio`
- Handle multiple connected users at the same time
- Keep things simple — no database, no frontend, no authentication

---

## 3. How It Works (High Level)

The app has two parts:

- **Server** — runs on one machine, manages all connections, and broadcasts messages to every connected user
- **Client** — runs on each user's machine, connects to the server, and lets the user send and receive messages

```
User A (client) ──┐
User B (client) ──┼──► Server ──► broadcasts to all connected clients
User C (client) ──┘
```

---

## 4. Features

### 4.1 Core Features

| Feature | Description |
|---|---|
| Connect with a username | Users pick a username when they join |
| Send messages | Type a message and press Enter to send it to everyone |
| Receive messages | Messages from other users appear in real time |
| Join/leave notifications | Everyone is notified when a user joins or leaves |
| Online user list | Users can see who's currently connected |

### 4.2 Slash Commands

Slash commands are special inputs that start with `/` and trigger a specific action instead of sending a regular message.

| Command | What It Does |
|---|---|
| `/help` | Shows a list of all available commands |
| `/users` | Prints the list of users currently online |
| `/nick <new_name>` | Changes your display username |
| `/dm <username> <message>` | Sends a private message to one user |
| `/clear` | Clears your terminal screen |
| `/quit` | Disconnects from the server and exits |

**Example usage:**
```
> /dm alice hey, are you there?
[DM to alice]: hey, are you there?

> /nick cooldev
Your username has been changed to cooldev.

> /users
Online now: alice, bob, cooldev
```

### 4.3 Message Display Format

Messages in the terminal should follow a clear, readable format:

```
[10:45] alice: hello everyone!
[10:46] bob: hey alice!
[10:46] *** charlie has joined the chat ***
[10:47] [DM from alice]: hey just you
[10:50] *** bob has left the chat ***
```

---

## 5. Tech Stack

| Layer | Tool | Why |
|---|---|---|
| Language | Python 3.10+ | Beginner-friendly, great async support |
| WebSocket server | `websockets` library | Simple Python WebSocket implementation |
| Async runtime | `asyncio` (built-in) | Handles multiple connections without threads |
| Terminal UI | `sys`, `input()` | No extra libraries needed |
| Config (optional) | `argparse` (built-in) | For passing host/port as command-line args |

**Install the only external dependency:**
```bash
pip install websockets
```

No database, no framework, no frontend. Just Python.

---

## 6. Project Structure

```
termchat/
├── server.py       # WebSocket server — manages connections and broadcasts
├── client.py       # Client — connects to server, handles input/output
└── README.md       # How to run the project
```

---

## 7. How to Run

**Start the server:**
```bash
python server.py --port 8765
```

**Connect as a client (in a separate terminal):**
```bash
python client.py --host localhost --port 8765 --username alice
```

Multiple users can connect by opening more terminals and running the client command with different usernames.

---

## 8. Server Behavior

The server should:

- Accept incoming WebSocket connections
- Ask for (or receive) the user's chosen username on connect
- Keep a dictionary of all active connections: `{ username: websocket }`
- When a message arrives, check if it's a slash command or a regular message
- For regular messages, broadcast to all connected clients
- For `/dm`, send only to the target user
- Handle disconnects cleanly and notify remaining users

---

## 9. Client Behavior

The client should:

- Connect to the server on startup
- Run two tasks simultaneously using `asyncio`:
  - **Receive task** — listens for incoming messages and prints them
  - **Send task** — waits for user keyboard input and sends it to the server
- Parse slash commands locally where possible (e.g., `/clear`, `/quit`)
- Send other slash commands to the server to handle (e.g., `/users`, `/dm`)

---

## 10. What's Out of Scope (Keep It Simple)

These features are intentionally left out for a beginner assignment:

- User accounts or passwords
- Chat rooms or channels
- Persistent message history
- File sharing
- A graphical interface (GUI)
- Deployment to a cloud server

---

## 11. Suggested Milestones

This assignment can be broken into steps:

1. **Step 1** — Run a basic WebSocket echo server and connect a single client
2. **Step 2** — Support multiple clients; broadcast messages to all of them
3. **Step 3** — Add usernames and join/leave notifications
4. **Step 4** — Implement slash commands (`/help`, `/users`, `/quit`)
5. **Step 5** — Add `/dm` for private messages and `/nick` to rename
6. **Step 6** — Polish: timestamps, clean disconnect handling, `/clear`

---

## 12. Acceptance Criteria

The assignment is complete when:

- [ ] Two or more clients can connect and chat in real time
- [ ] Messages show the sender's username and a timestamp
- [ ] All six slash commands work correctly
- [ ] `/dm` only delivers the message to the target user
- [ ] Joining and leaving is announced to the group
- [ ] The server handles a client disconnecting without crashing

---

## 13. GitHub Workflow Guide

This section explains how to use Git and GitHub properly while working on this assignment. Each milestone from Section 11 should live on its own branch so your work is organized and easy to review.

---

### 13.1 First-Time Setup

**Step 1 — Create the repo on GitHub**

Go to github.com → click **New repository** → name it `termchat` → set it to Public → click **Create repository**.

**Step 2 — Clone it to your machine**

```bash
git clone https://github.com/your-username/termchat.git
cd termchat
```

**Step 3 — Confirm you're on `main`**

```bash
git branch
# should show: * main
```

---

### 13.2 Branch Naming Convention

Use a consistent naming pattern so branches are easy to identify:

```
feature/<short-description>
```

| Milestone | Branch Name |
|---|---|
| Echo server + single client | `feature/echo-server` |
| Multi-client broadcasting | `feature/broadcast` |
| Usernames & notifications | `feature/usernames` |
| Slash commands | `feature/slash-commands` |
| DMs and /nick | `feature/dm-and-nick` |
| Polish & cleanup | `feature/polish` |

---

### 13.3 Working on a Feature Branch

Every time you start a new milestone, follow these steps:

**1. Make sure `main` is up to date first**

```bash
git checkout main
git pull origin main
```

**2. Create and switch to a new branch**

```bash
git checkout -b feature/broadcast
```

This creates the branch and moves you onto it in one command.

**3. Do your work**

Write your code, test it, make sure it runs. Then stage and commit your changes:

```bash
git add .
git commit -m "feat: broadcast messages to all connected clients"
```

Write short, clear commit messages. A good format is:

```
feat: what you added
fix: what you fixed
refactor: what you cleaned up
```

**4. Push the branch to GitHub**

```bash
git push origin feature/broadcast
```

---

### 13.4 Opening a Pull Request (PR)

Once your feature branch is pushed:

1. Go to your repo on GitHub
2. You'll see a banner: **"feature/broadcast had recent pushes — Compare & pull request"** — click it
3. Write a short description of what you built
4. Click **Create pull request**

A PR is a way to propose merging your branch into `main`. For a solo assignment, you can review your own code here before merging.

---

### 13.5 Merging Into Main

Once you're happy with the PR:

1. Click **Merge pull request** on GitHub
2. Click **Confirm merge**
3. Then pull the updated `main` locally:

```bash
git checkout main
git pull origin main
```

You can now delete the feature branch since it's been merged:

```bash
git branch -d feature/broadcast              # deletes locally
git push origin --delete feature/broadcast   # deletes on GitHub
```

---

### 13.6 Keeping Your Branch Up to Date

If you're working on a long-running branch and `main` gets updated, sync your branch like this:

```bash
git checkout feature/slash-commands
git merge main
```

This pulls the latest changes from `main` into your current branch so you're not working on outdated code.

---

### 13.7 Quick Reference Cheat Sheet

```bash
# See which branch you're on
git branch

# See all branches (local + remote)
git branch -a

# Switch to an existing branch
git checkout feature/broadcast

# Create a new branch and switch to it
git checkout -b feature/new-thing

# Stage all changes
git add .

# Commit with a message
git commit -m "feat: add /nick command"

# Push your branch to GitHub
git push origin feature/new-thing

# Pull latest changes from main
git checkout main && git pull origin main
```

---

### 13.8 What Your Branch History Should Look Like

By the end of the assignment, your GitHub repo should show a clean history of merged branches, one per milestone:

```
main
 ├── ← feature/echo-server      (Step 1)
 ├── ← feature/broadcast        (Step 2)
 ├── ← feature/usernames        (Step 3)
 ├── ← feature/slash-commands   (Step 4)
 ├── ← feature/dm-and-nick      (Step 5)
 └── ← feature/polish           (Step 6)
```

This shows a clear, reviewable progression of your work — and is great practice for how real teams use Git.

---

## 14. Resources

- Python `websockets` docs: https://websockets.readthedocs.io
- Python `asyncio` intro: https://docs.python.org/3/library/asyncio.html
- `argparse` tutorial: https://docs.python.org/3/howto/argparse.html
- Git branching basics: https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging
- GitHub Pull Requests guide: https://docs.github.com/en/pull-requests
