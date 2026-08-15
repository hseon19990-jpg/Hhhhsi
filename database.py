import sqlite3
import os
from config import DB_PATH

if not os.path.exists("data"):
    os.makedirs("data")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE,
            session_string TEXT,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            messages_sent INTEGER DEFAULT 0,
            last_activity TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_link TEXT UNIQUE,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sent_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER,
            group_id INTEGER,
            clip_id INTEGER,
            sent_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('timer', '60')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('status', 'true')")
    
    conn.commit()
    conn.close()

# ========== دوال الحسابات ==========
def add_account(phone, session_string):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO accounts (phone, session_string, last_activity) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (phone, session_string)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def get_accounts():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM accounts ORDER BY added_date DESC")
    data = cursor.fetchall()
    conn.close()
    return data

def get_account(phone):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM accounts WHERE phone = ?", (phone,))
    data = cursor.fetchone()
    conn.close()
    return data

def delete_account(phone):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM accounts WHERE phone = ?", (phone,))
    conn.commit()
    conn.close()

def update_account_session(phone, session_string):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE accounts SET session_string = ?, last_activity = CURRENT_TIMESTAMP WHERE phone = ?",
        (session_string, phone)
    )
    conn.commit()
    conn.close()

def increment_messages(phone):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE accounts SET messages_sent = messages_sent + 1, last_activity = CURRENT_TIMESTAMP WHERE phone = ?",
        (phone,)
    )
    conn.commit()
    conn.close()

def reset_daily_messages():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE accounts SET messages_sent = 0")
    conn.commit()
    conn.close()

# ========== دوال الكليشات ==========
def add_clip(text):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO clips (text) VALUES (?)", (text,))
    conn.commit()
    conn.close()

def get_clips():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clips ORDER BY added_date DESC")
    data = cursor.fetchall()
    conn.close()
    return data

def delete_clip(clip_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clips WHERE id = ?", (clip_id,))
    conn.commit()
    conn.close()

# ========== دوال الكروبات ==========
def add_group(group_link):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO groups (group_link) VALUES (?)", (group_link,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def get_groups():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM groups WHERE is_active = 1 ORDER BY added_date DESC")
    data = cursor.fetchall()
    conn.close()
    return data

def delete_group(group_link):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM groups WHERE group_link = ?", (group_link,))
    conn.commit()
    conn.close()

def deactivate_group(group_link):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE groups SET is_active = 0 WHERE group_link = ?", (group_link,))
    conn.commit()
    conn.close()

# ========== دوال الإعدادات ==========
def get_setting(key):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except:
        return None

def set_setting(key, value):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

# ========== دوال سجل الإرسال ==========
def log_sent(account_id, group_id, clip_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sent_log (account_id, group_id, clip_id) VALUES (?, ?, ?)",
        (account_id, group_id, clip_id)
    )
    conn.commit()
    conn.close()

def has_sent_today(account_id, group_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM sent_log WHERE account_id = ? AND group_id = ? AND date(sent_date) = date('now')",
        (account_id, group_id)
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0
