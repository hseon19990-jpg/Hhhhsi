import sqlite3
import os
from config import DB_PATH

# التأكد من وجود مجلد data
if not os.path.exists("data"):
    os.makedirs("data")

def init_db():
    """إنشاء الجداول في قاعدة البيانات"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # جدول الحسابات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول الكليشات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول الكروبات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id TEXT UNIQUE,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول الإعدادات (تم التعديل)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # إضافة إعدادات افتراضية (تم التعديل)
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('timer', '60')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('status', 'true')")
    
    conn.commit()
    conn.close()

# ========== دوال الحسابات ==========
def add_account(username):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO accounts (username) VALUES (?)", (username,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        print(f"خطأ في اضافة حساب: {e}")
        return False

def get_accounts():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM accounts ORDER BY added_date DESC")
    data = cursor.fetchall()
    conn.close()
    return data

def delete_account(username):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM accounts WHERE username = ?", (username,))
    conn.commit()
    conn.close()

def delete_all_accounts():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM accounts")
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

def delete_all_clips():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clips")
    conn.commit()
    conn.close()

# ========== دوال الكروبات ==========
def add_group(group_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO groups (group_id) VALUES (?)", (group_id,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        print(f"خطأ في اضافة كروب: {e}")
        return False

def get_groups():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM groups ORDER BY added_date DESC")
    data = cursor.fetchall()
    conn.close()
    return data

def delete_group(group_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM groups WHERE group_id = ?", (group_id,))
    conn.commit()
    conn.close()

def delete_all_groups():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM groups")
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
    except sqlite3.OperationalError:
        # إذا كان الجدول غير موجود، ننشئه
        init_db()
        return get_setting(key)

def set_setting(key, value):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        conn.close()
        return True
    except sqlite3.OperationalError:
        # إذا كان الجدول غير موجود، ننشئه
        init_db()
        return set_setting(key, value)
