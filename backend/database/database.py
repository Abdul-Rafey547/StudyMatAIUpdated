import sqlite3
import os

DATABASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database')
DATABASE_FILE = os.path.join(DATABASE_DIR, 'studymate.db')
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), 'schema.sql')

def get_db_connection():
    if not os.path.exists(DATABASE_DIR):
        os.makedirs(DATABASE_DIR, exist_ok=True)

    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON;')
    return conn

def init_db():
    conn = get_db_connection()
    with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

# Automatically initialize database if it doesn't exist
if not os.path.exists(DATABASE_FILE):
    init_db()
