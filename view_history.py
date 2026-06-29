import sqlite3
import os

db_path = os.path.join(
    os.path.expanduser("~"),
    ".termchat",
    "history.db"
)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT * FROM messages")

for row in cursor.fetchall():
    print(row)

    conn.close()