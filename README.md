# TeleSync (Tchat)

A real-time terminal-based chat application built with Python.

TeleSync is a command-line communication platform that allows multiple users to connect and chat in real time. It provides a lightweight, fast, and customizable chatting experience directly from the terminal.

---

# 🚀 Features

## Real-Time Communication
- Real-time messaging between multiple users
- Client-server architecture
- Multiple users can connect simultaneously

## User Management
- Custom username support
- Change username anytime
- User status system

## Status System
Users can set their current status:

- Online
- Idle
- Busy
- Coding
- Away

## Private Messaging
- Send direct messages to specific users

## Terminal UI
- Clean terminal interface
- Rich formatted output
- Multiple themes support

Available themes:
- Dark
- Hacker
- Dracula
- Nord

## Command System
Powerful command-based interaction system with help support.

---

# 📥 Installation

## Requirements

Before installing TeleSync, make sure you have:

- Python 3.10 or above
- pip package manager
- Git


## Clone Repository

Download the project using:

```bash
git clone <repository-url>
```

Example:

```bash
git clone https://github.com/username/telesync.git
```


## Navigate to Project Folder

```bash
cd telesync
```


## Install Dependencies

Install all required Python packages:

```bash
pip install -r requirements.txt
```

---

# ▶️ Running TeleSync

TeleSync works using a client-server architecture.

## Start Server

Open a terminal and run:

```bash
python server/server.py
```

The server will start waiting for client connections.


## Start Client

Open another terminal window:

```bash
python client/client.py
```

Enter your username and connect to the server.

Example:

```
Enter username: Kaif

Connected successfully!
```

---

# 💬 Commands Guide

Use:

```
/help
```

to view all available commands.

---

## Show Online User Count

Command:

```
/count
```

Description:

Shows the number of currently connected users.

---

## Private Message

Command:

```
/dm <username> <message>
```

Example:

```
/dm John Hello
```

Sends a private message to a specific user.

---

## Change Username

Command:

```
/nick <newname>
```

Example:

```
/nick Kaif
```

Changes your current username.

---

## Change Status

Command:

```
/status <state>
```

Available options:

```
Online
Idle
Busy
Coding
Away
```

Example:

```
/status Coding
```

---

## Change Theme

Command:

```
/theme <name>
```

Available themes:

```
Dark
Hacker
Dracula
Nord
```

Example:

```
/theme Hacker
```

---

## Show Help

Command:

```
/help
```

Displays all available commands and their usage.

---

## Exit Application

Command:

```
/quit
```

Disconnects from the server and closes the application.

---

# 📂 Project Structure

```
TeleSync/

│
├── client/
│   ├── client.py
│   └── ui.py
│
├── server/
│   └── server.py
│
├── shared/
│   └── models.py
│
├── requirements.txt
│
└── README.md
```

---

# ⚙️ Configuration

You can configure:

- Server host
- Server port
- Client settings
- UI preferences

according to your requirements.

---

# 🛠️ Troubleshooting

## Connection Error

Check:

- Server is running
- Correct host and port are configured
- Network connection is available


## Package Installation Error

Run:

```bash
pip install --upgrade pip
```

Then install dependencies again:

```bash
pip install -r requirements.txt
```

---

# 🔮 Future Improvements

Planned features:

- File sharing
- Voice communication
- Mobile application
- User authentication
- Database support
- End-to-end encryption
- Cloud deployment

---

# 🤝 Contributing

Contributions are welcome.

Steps:

1. Fork the repository
2. Create a new branch
3. Make your changes
4. Submit a pull request

---

# 📜 License

This project is licensed under the MIT License.

---

# 👨‍💻 Author

Created by **Kaif**
