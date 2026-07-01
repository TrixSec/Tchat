import os
import sqlite3

DB_DIR = os.path.join(os.path.expanduser("~"), ".termchat")
DB_PATH = os.path.join(DB_DIR, "history.db")

def init_db():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            msg_id INTEGER,
            type TEXT,
            sender TEXT,
            recipient TEXT,
            content TEXT,
            reply_to INTEGER,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_message(msg_id, msg_type, sender, recipient, content, reply_to, timestamp):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO messages (msg_id, type, sender, recipient, content, reply_to, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (msg_id, msg_type, sender, recipient, content, reply_to, timestamp))
        conn.commit()
        conn.close()
    except Exception as e:
        pass

def get_history(limit=50):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT msg_id, type, sender, recipient, content, reply_to, timestamp 
            FROM messages 
            ORDER BY id DESC 
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        # Return in chronological order
        return list(reversed(rows))
    except Exception as e:
        return []

def search_history(query="", sender=None, msg_type=None, limit=None, case_sensitive=False):
    try:
        conn = sqlite3.connect(DB_PATH)
        if case_sensitive:
            conn.execute("PRAGMA case_sensitive_like = ON;")
        else:
            conn.execute("PRAGMA case_sensitive_like = OFF;")
            
        cursor = conn.cursor()
        
        sql = """
            SELECT msg_id, type, sender, recipient, content, reply_to, timestamp 
            FROM messages 
            WHERE 1=1
        """
        params = []
        if query:
            sql += " AND content LIKE ?"
            params.append(f"%{query}%")
            
        if sender:
            sql += " AND sender LIKE ?"
            params.append(sender)
            
        if msg_type:
            sql += " AND type = ?"
            params.append(msg_type)
            
        sql += " ORDER BY id ASC"
        
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
            
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        return []
