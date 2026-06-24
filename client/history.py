import sqlite3
import os
import platform

from client.ui import console

class HistoryManager:
    def __init__(self):
        self.db_path = self._get_db_path()
        self._init_db()

    def _get_db_path(self):
        if platform.system() == "Windows":
            base_dir = os.path.join(os.environ.get("USERPROFILE", ""), ".termchat")
        else:
            base_dir = os.path.expanduser("~/.termchat")
            
        try:
            os.makedirs(base_dir, exist_ok=True)
        except Exception:
            pass
            
        return os.path.join(base_dir, "history.db")

    def _get_connection(self):
        try:
            return sqlite3.connect(self.db_path)
        except Exception:
            return None

    def _init_db(self):
        conn = self._get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER,
                    timestamp TEXT,
                    username TEXT,
                    content TEXT,
                    reply_to INTEGER NULL,
                    message_type TEXT
                )
            ''')
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()

    def save_message(self, message_id, timestamp, username, content, reply_to, message_type):
        conn = self._get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO messages (message_id, timestamp, username, content, reply_to, message_type)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (message_id, timestamp, username, content, reply_to, message_type))
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()

    def get_recent(self, limit=20):
        conn = self._get_connection()
        if not conn:
            console.print("History database unavailable.", style="bold red")
            return []
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT message_id, timestamp, username, content, reply_to, message_type
                FROM messages
                ORDER BY id DESC
                LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()
            return list(reversed(rows))
        except Exception:
            console.print("History database unavailable.", style="bold red")
            return []
        finally:
            conn.close()

    def search(self, query):
        conn = self._get_connection()
        if not conn:
            console.print("History database unavailable.", style="bold red")
            return []
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT message_id, timestamp, username, content, reply_to, message_type
                FROM messages
                WHERE content LIKE ?
                ORDER BY id ASC
            ''', (f'%{query}%',))
            return cursor.fetchall()
        except Exception:
            console.print("History database unavailable.", style="bold red")
            return []
        finally:
            conn.close()

    def search_user(self, username):
        conn = self._get_connection()
        if not conn:
            console.print("History database unavailable.", style="bold red")
            return []
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT message_id, timestamp, username, content, reply_to, message_type
                FROM messages
                WHERE username LIKE ?
                ORDER BY id ASC
            ''', (f'%{username}%',))
            return cursor.fetchall()
        except Exception:
            console.print("History database unavailable.", style="bold red")
            return []
        finally:
            conn.close()
