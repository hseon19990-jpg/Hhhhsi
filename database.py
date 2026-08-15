"""
نظام قاعدة بيانات متطور للبوت
يدعم: SQLite و PostgreSQL مع إعادة محاولة تلقائية
"""

import sqlite3
import os
import json
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ==================== إعدادات قاعدة البيانات ====================

DB_PATH = os.environ.get("DB_PATH", "data/database.db")
DB_TYPE = os.environ.get("DB_TYPE", "sqlite")  # sqlite أو postgres

# التأكد من وجود مجلد البيانات
if not os.path.exists("data"):
    os.makedirs("data")

# ==================== دوال قاعدة البيانات ====================

def get_db_connection():
    """الحصول على اتصال بقاعدة البيانات"""
    if DB_TYPE == "postgres":
        import psycopg2
        import psycopg2.extras
        DATABASE_URL = os.environ.get("DATABASE_URL", "")
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL غير مضبوط")
        return psycopg2.connect(DATABASE_URL)
    else:
        return sqlite3.connect(DB_PATH)

def dict_factory(cursor, row):
    """تحويل الصف إلى قاموس (SQLite)"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def execute_query(query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False) -> Any:
    """
    تنفيذ استعلام مع إعادة محاولة تلقائية
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            conn = get_db_connection()
            
            if DB_TYPE == "postgres":
                cursor = conn.cursor()
            else:
                cursor = conn.cursor()
                cursor.row_factory = dict_factory
                
            # تحويل ? إلى %s لـ PostgreSQL
            if DB_TYPE == "postgres":
                query = query.replace("?", "%s")
                
            cursor.execute(query, params)
            
            if fetch_one:
                result = cursor.fetchone()
                conn.close()
                return result
            elif fetch_all:
                result = cursor.fetchall()
                conn.close()
                return result
            else:
                conn.commit()
                result = cursor.rowcount if hasattr(cursor, 'rowcount') else 0
                conn.close()
                return result
                
        except Exception as e:
            logger.warning(f"⚠️ محاولة {attempt + 1} فشلت: {e}")
            if attempt == max_retries - 1:
                raise
                
    return None

# ==================== تهيئة قاعدة البيانات ====================

def init_db():
    """تهيئة جميع الجداول"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # === جدول الحسابات ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT UNIQUE NOT NULL,
                session_string TEXT,
                session_type TEXT DEFAULT 'string',
                api_id INTEGER,
                api_hash TEXT,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                messages_sent INTEGER DEFAULT 0,
                last_activity TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                is_solo INTEGER DEFAULT 0,
                can_send_code INTEGER DEFAULT 0,
                last_authorized INTEGER DEFAULT 1,
                last_device_count INTEGER DEFAULT -1,
                twofa_password TEXT,
                auto_2fa_enabled INTEGER DEFAULT 0,
                twofa_reset_date TIMESTAMP,
                sessions_reset INTEGER DEFAULT 0,
                force_listed INTEGER DEFAULT 0,
                ever_sold INTEGER DEFAULT 0,
                frozen_at TIMESTAMP,
                deleted_at TIMESTAMP,
                kicked_at TIMESTAMP,
                forced_ref_excluded INTEGER DEFAULT 0,
                referral_only INTEGER DEFAULT 0,
                bot_session_ip TEXT
            )
        ''')
        
        # === جدول الكليشات ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # === جدول الكروبات ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_link TEXT UNIQUE NOT NULL,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # === جدول الإعدادات ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # === جدول سجل الإرسال ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sent_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER,
                group_id INTEGER,
                clip_id INTEGER,
                sent_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # === جدول الجلسات المدورة ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rotated_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT,
                old_session TEXT,
                rotated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # === جدول المستخدمين ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                points INTEGER DEFAULT 0,
                invited_by INTEGER DEFAULT 0,
                total_orders INTEGER DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                bot_user_num INTEGER,
                verified INTEGER DEFAULT 0,
                banned INTEGER DEFAULT 0,
                banned_at TIMESTAMP,
                ban_reason TEXT,
                referral_credited INTEGER DEFAULT 0,
                credited_at TIMESTAMP,
                referral_points_blocked INTEGER DEFAULT 0
            )
        ''')
        
        # === جدول الأوامر ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                service_id INTEGER,
                link TEXT,
                quantity INTEGER,
                cost_points INTEGER DEFAULT 0,
                cost_stars INTEGER DEFAULT 0,
                api_order_id TEXT DEFAULT '',
                status TEXT DEFAULT 'pending',
                order_code TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                partial_refund_pts INTEGER DEFAULT 0
            )
        ''')
        
        # === جدول الخدمات ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                api_service_id INTEGER,
                panel INTEGER DEFAULT 1,
                platform TEXT DEFAULT 'tg',
                name_ar TEXT,
                description TEXT,
                min_qty INTEGER,
                max_qty INTEGER,
                price_per_point REAL,
                active INTEGER DEFAULT 1,
                service_type TEXT DEFAULT 'smm'
            )
        ''')
        
        # === جدول القنوات الإجبارية ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mandatory_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_username TEXT UNIQUE,
                channel_title TEXT,
                owner_user_id INTEGER DEFAULT 0,
                funding_type TEXT DEFAULT 'mandatory',
                active INTEGER DEFAULT 1,
                queued INTEGER DEFAULT 0
            )
        ''')
        
        # === جدول تمويل القنوات ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS channel_funding (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                channel_username TEXT,
                funding_type TEXT,
                cost_points INTEGER,
                target_members INTEGER DEFAULT 0,
                current_members INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # === جدول الجوائز ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_prizes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                quantity INTEGER DEFAULT 1,
                points_cost INTEGER NOT NULL,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # === جدول الهدايا اليومية ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_gifts (
                user_id INTEGER PRIMARY KEY,
                last_claim TEXT
            )
        ''')
        
        # === جدول مكافآت الانضمام للقنوات ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS channel_join_rewards (
                user_id INTEGER,
                channel_id INTEGER,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, channel_id)
            )
        ''')
        
        # === جدول الأكواد الترويجية ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS promo_codes (
                code TEXT PRIMARY KEY,
                max_uses INTEGER DEFAULT 1,
                used_count INTEGER DEFAULT 0,
                points INTEGER DEFAULT 0,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # === جدول استخدام الأكواد ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS promo_uses (
                code TEXT,
                user_id INTEGER,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (code, user_id)
            )
        ''')
        
        # === جدول أكواد شراء الأرقام ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS number_purchase_codes (
                code TEXT PRIMARY KEY,
                max_uses INTEGER DEFAULT 1,
                used_count INTEGER DEFAULT 0,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # === جدول استخدام أكواد الأرقام ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS number_purchase_code_uses (
                code TEXT,
                user_id INTEGER,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (code, user_id)
            )
        ''')
        
        # === جدول مهام الإحالة ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referral_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                bot_username TEXT NOT NULL,
                start_param TEXT NOT NULL,
                mandatory_channels TEXT DEFAULT '',
                folder_link TEXT DEFAULT '',
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # === جدول إكمال الإحالات ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referral_completions (
                task_id INTEGER,
                stock_id INTEGER,
                status TEXT DEFAULT 'pending',
                done_at TIMESTAMP,
                error_msg TEXT,
                PRIMARY KEY (task_id, stock_id)
            )
        ''')
        
        # === جدول طلبات الإحالة الإجبارية ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS forced_ref_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                bot_username TEXT NOT NULL,
                start_param TEXT NOT NULL,
                channels TEXT DEFAULT '',
                quantity INTEGER NOT NULL,
                cost_points INTEGER NOT NULL,
                cost_stars INTEGER DEFAULT 0,
                payment_method TEXT DEFAULT 'points',
                done_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                reactivated_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                order_code TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # === جدول طلبات الاشتراك الإجباري ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mandatory_sub_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                bot_username TEXT NOT NULL,
                start_param TEXT NOT NULL,
                channels TEXT DEFAULT '',
                quantity INTEGER NOT NULL,
                cost_points INTEGER NOT NULL,
                done_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                reactivated_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                order_code TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # === جدول المشرفين ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS supervisors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                username TEXT DEFAULT '',
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # === جدول حسابات المشرفين ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS supervisor_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supervisor_id INTEGER NOT NULL,
                phone_number TEXT NOT NULL,
                session_string TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(supervisor_id, phone_number)
            )
        ''')
        
        # === جدول الإعدادات الافتراضية ===
        default_settings = [
            ('timer', '60'),
            ('status', 'true'),
            ('referral_points', '30'),
            ('daily_gift_points', '50'),
            ('star_to_points', '250'),
            ('exchange_star_rate', '2000'),
            ('telegram_number_cost', '5000'),
            ('mandatory_channel_cost', '200'),
            ('internal_channel_cost', '100'),
            ('welcome_message', 'أهلاً بك في البوت!'),
            ('referral_task_delay', '30'),
            ('channel_leave_penalty', '75'),
            ('internal_leave_grace_hours', '24'),
            ('captcha_enabled', '0'),
            ('maintenance_mode', '0'),
            ('number_exchange_enabled', '0'),
            ('legendary_services_visible', '1'),
        ]
        
        for key, value in default_settings:
            cursor.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )
        
        conn.commit()
        conn.close()
        
        logger.info("✅ تم تهيئة قاعدة البيانات بنجاح")
        
    except Exception as e:
        logger.error(f"❌ فشل تهيئة قاعدة البيانات: {e}")
        raise

# ==================== دوال الحسابات ====================

def add_account(phone: str, session_string: str, session_type: str = "string") -> bool:
    """إضافة حساب جديد"""
    try:
        execute_query(
            "INSERT INTO accounts (phone, session_string, session_type, last_activity) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (phone, session_string, session_type)
        )
        return True
    except Exception:
        return False

def get_accounts(active_only: bool = True) -> List[Dict[str, Any]]:
    """الحصول على قائمة الحسابات"""
    query = "SELECT * FROM accounts"
    if active_only:
        query += " WHERE is_active = 1 AND deleted_at IS NULL"
    query += " ORDER BY added_date DESC"
    return execute_query(query, fetch_all=True) or []

def get_account(phone: str) -> Optional[Dict[str, Any]]:
    """الحصول على حساب برقم الهاتف"""
    result = execute_query(
        "SELECT * FROM accounts WHERE phone = ?",
        (phone,),
        fetch_one=True
    )
    return result

def get_account_by_id(account_id: int) -> Optional[Dict[str, Any]]:
    """الحصول على حساب بالمعرف"""
    result = execute_query(
        "SELECT * FROM accounts WHERE id = ?",
        (account_id,),
        fetch_one=True
    )
    return result

def update_account_session(phone: str, session_string: str) -> bool:
    """تحديث جلسة الحساب"""
    try:
        execute_query(
            "UPDATE accounts SET session_string = ?, last_activity = CURRENT_TIMESTAMP WHERE phone = ?",
            (session_string, phone)
        )
        return True
    except Exception:
        return False

def delete_account(phone: str) -> bool:
    """حذف حساب (ناعم)"""
    try:
        execute_query(
            "UPDATE accounts SET deleted_at = CURRENT_TIMESTAMP, is_active = 0 WHERE phone = ?",
            (phone,)
        )
        return True
    except Exception:
        return False

def hard_delete_account(phone: str) -> bool:
    """حذف حساب (نهائي)"""
    try:
        execute_query("DELETE FROM accounts WHERE phone = ?", (phone,))
        return True
    except Exception:
        return False

def increment_messages(phone: str) -> bool:
    """زيادة عداد الرسائل المرسلة"""
    try:
        execute_query(
            "UPDATE accounts SET messages_sent = messages_sent + 1, last_activity = CURRENT_TIMESTAMP WHERE phone = ?",
            (phone,)
        )
        return True
    except Exception:
        return False

def reset_daily_messages() -> bool:
    """إعادة تعيين عداد الرسائل اليومي"""
    try:
        execute_query("UPDATE accounts SET messages_sent = 0")
        return True
    except Exception:
        return False

def set_account_solo(phone: str, is_solo: bool) -> bool:
    """تعيين حالة الجلسة الوحيدة"""
    try:
        execute_query(
            "UPDATE accounts SET is_solo = ? WHERE phone = ?",
            (1 if is_solo else 0, phone)
        )
        return True
    except Exception:
        return False

def set_can_send_code(phone: str, can_send: bool) -> bool:
    """تعيين إمكانية إرسال الكود"""
    try:
        execute_query(
            "UPDATE accounts SET can_send_code = ? WHERE phone = ?",
            (1 if can_send else 0, phone)
        )
        return True
    except Exception:
        return False

def set_twofa_password(phone: str, password: str) -> bool:
    """حفظ كلمة مرور 2FA"""
    try:
        execute_query(
            "UPDATE accounts SET twofa_password = ?, auto_2fa_enabled = 1 WHERE phone = ?",
            (password, phone)
        )
        return True
    except Exception:
        return False

def set_2fa_reset_date(phone: str, reset_date: datetime) -> bool:
    """تعيين تاريخ إعادة تعيين 2FA"""
    try:
        execute_query(
            "UPDATE accounts SET twofa_reset_date = ? WHERE phone = ?",
            (reset_date, phone)
        )
        return True
    except Exception:
        return False

def save_rotated_session(phone: str, old_session: str) -> bool:
    """حفظ جلسة مدورة"""
    try:
        execute_query(
            "INSERT INTO rotated_sessions (phone, old_session) VALUES (?, ?)",
            (phone, old_session)
        )
        return True
    except Exception:
        return False

# ==================== دوال الكليشات ====================

def add_clip(text: str) -> bool:
    """إضافة كليشة جديدة"""
    try:
        execute_query("INSERT INTO clips (text) VALUES (?)", (text,))
        return True
    except Exception:
        return False

def get_clips() -> List[Dict[str, Any]]:
    """الحصول على جميع الكليشات"""
    return execute_query("SELECT * FROM clips ORDER BY added_date DESC", fetch_all=True) or []

def delete_clip(clip_id: int) -> bool:
    """حذف كليشة"""
    try:
        execute_query("DELETE FROM clips WHERE id = ?", (clip_id,))
        return True
    except Exception:
        return False

def delete_all_clips() -> bool:
    """حذف جميع الكليشات"""
    try:
        execute_query("DELETE FROM clips")
        return True
    except Exception:
        return False

# ==================== دوال الكروبات ====================

def add_group(group_link: str) -> bool:
    """إضافة كروب جديد"""
    try:
        execute_query(
            "INSERT INTO groups (group_link) VALUES (?)",
            (group_link,)
        )
        return True
    except Exception:
        return False

def get_groups(active_only: bool = True) -> List[Dict[str, Any]]:
    """الحصول على قائمة الكروبات"""
    query = "SELECT * FROM groups"
    if active_only:
        query += " WHERE is_active = 1"
    query += " ORDER BY added_date DESC"
    return execute_query(query, fetch_all=True) or []

def delete_group(group_link: str) -> bool:
    """حذف كروب"""
    try:
        execute_query(
            "UPDATE groups SET is_active = 0 WHERE group_link = ?",
            (group_link,)
        )
        return True
    except Exception:
        return False

def hard_delete_group(group_link: str) -> bool:
    """حذف كروب (نهائي)"""
    try:
        execute_query("DELETE FROM groups WHERE group_link = ?", (group_link,))
        return True
    except Exception:
        return False

# ==================== دوال الكروبات (إضافية) ====================

def deactivate_group(group_link: str) -> bool:
    """تعطيل كروب (بدلاً من حذفه)"""
    try:
        execute_query(
            "UPDATE groups SET is_active = 0 WHERE group_link = ?",
            (group_link,)
        )
        return True
    except Exception:
        return False

def activate_group(group_link: str) -> bool:
    """تفعيل كروب"""
    try:
        execute_query(
            "UPDATE groups SET is_active = 1 WHERE group_link = ?",
            (group_link,)
        )
        return True
    except Exception:
        return False

# ==================== دوال الإعدادات ====================

def get_setting(key: str) -> Optional[str]:
    """الحصول على إعداد"""
    try:
        result = execute_query(
            "SELECT value FROM settings WHERE key = ?",
            (key,),
            fetch_one=True
        )
        return result["value"] if result else None
    except Exception:
        return None

def set_setting(key: str, value: str) -> bool:
    """تعيين إعداد"""
    try:
        execute_query(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        return True
    except Exception:
        return False

# ==================== دوال سجل الإرسال ====================

def log_sent(account_id: int, group_id: int, clip_id: int) -> bool:
    """تسجيل عملية إرسال"""
    try:
        execute_query(
            "INSERT INTO sent_log (account_id, group_id, clip_id) VALUES (?, ?, ?)",
            (account_id, group_id, clip_id)
        )
        return True
    except Exception:
        return False

def has_sent_today(account_id: int, group_id: int) -> bool:
    """التحقق من إرسال اليوم"""
    try:
        result = execute_query(
            "SELECT COUNT(*) as count FROM sent_log WHERE account_id = ? AND group_id = ? AND date(sent_date) = date('now')",
            (account_id, group_id),
            fetch_one=True
        )
        return result["count"] > 0 if result else False
    except Exception:
        return False

def get_sent_count_today(account_id: int) -> int:
    """الحصول على عدد الإرسالات اليومية لحساب"""
    try:
        result = execute_query(
            "SELECT COUNT(*) as count FROM sent_log WHERE account_id = ? AND date(sent_date) = date('now')",
            (account_id,),
            fetch_one=True
        )
        return result["count"] if result else 0
    except Exception:
        return 0

# ==================== دوال المستخدمين ====================

def get_or_create_user(user_id: int, username: str = "", full_name: str = "", invited_by: int = 0) -> Dict[str, Any]:
    """الحصول على مستخدم أو إنشاؤه"""
    try:
        user = execute_query(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,),
            fetch_one=True
        )
        
        if user:
            # تحديث البيانات
            execute_query(
                "UPDATE users SET username = ?, full_name = ? WHERE user_id = ?",
                (username, full_name, user_id)
            )
            return user
            
        # إنشاء مستخدم جديد
        bot_num_result = execute_query(
            "SELECT COALESCE(MAX(bot_user_num), 0) + 1 as num FROM users",
            fetch_one=True
        )
        bot_num = bot_num_result["num"] if bot_num_result else 1
        
        execute_query(
            "INSERT INTO users (user_id, username, full_name, invited_by, bot_user_num) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, full_name, invited_by, bot_num)
        )
        
        return execute_query(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,),
            fetch_one=True
        )
        
    except Exception as e:
        logger.error(f"❌ فشل الحصول على المستخدم: {e}")
        return {}

def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """الحصول على مستخدم"""
    return execute_query(
        "SELECT * FROM users WHERE user_id = ?",
        (user_id,),
        fetch_one=True
    )

def add_points(user_id: int, points: int) -> bool:
    """إضافة نقاط للمستخدم"""
    try:
        execute_query(
            "UPDATE users SET points = points + ? WHERE user_id = ?",
            (points, user_id)
        )
        return True
    except Exception:
        return False

def deduct_points(user_id: int, points: int) -> bool:
    """خصم نقاط من المستخدم"""
    try:
        execute_query(
            "UPDATE users SET points = points - ? WHERE user_id = ? AND points >= ?",
            (points, user_id, points)
        )
        return True
    except Exception:
        return False

def get_user_points(user_id: int) -> int:
    """الحصول على نقاط المستخدم"""
    result = execute_query(
        "SELECT points FROM users WHERE user_id = ?",
        (user_id,),
        fetch_one=True
    )
    return result["points"] if result else 0

# ==================== دوال الخدمات ====================

def add_service(category: str, api_service_id: int, panel: int, platform: str, name: str, description: str, min_qty: int, max_qty: int, price: float) -> bool:
    """إضافة خدمة جديدة"""
    try:
        execute_query(
            """INSERT INTO services 
               (category, api_service_id, panel, platform, name_ar, description, min_qty, max_qty, price_per_point) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (category, api_service_id, panel, platform, name, description, min_qty, max_qty, price)
        )
        return True
    except Exception:
        return False

def get_services(category: str = None, platform: str = None, active_only: bool = True) -> List[Dict[str, Any]]:
    """الحصول على قائمة الخدمات"""
    query = "SELECT * FROM services WHERE 1=1"
    params = []
    
    if category:
        query += " AND category = ?"
        params.append(category)
    
    if platform:
        query += " AND platform = ?"
        params.append(platform)
    
    if active_only:
        query += " AND active = 1"
    
    query += " ORDER BY category, id"
    
    return execute_query(query, tuple(params), fetch_all=True) or []

def get_service(service_id: int) -> Optional[Dict[str, Any]]:
    """الحصول على خدمة"""
    return execute_query(
        "SELECT * FROM services WHERE id = ?",
        (service_id,),
        fetch_one=True
    )

def update_service(service_id: int, **kwargs) -> bool:
    """تحديث خدمة"""
    try:
        fields = []
        params = []
        
        for key, value in kwargs.items():
            fields.append(f"{key} = ?")
            params.append(value)
        
        params.append(service_id)
        
        execute_query(
            f"UPDATE services SET {', '.join(fields)} WHERE id = ?",
            tuple(params)
        )
        return True
    except Exception:
        return False

def delete_service(service_id: int) -> bool:
    """حذف خدمة"""
    try:
        execute_query("DELETE FROM services WHERE id = ?", (service_id,))
        return True
    except Exception:
        return False

# ==================== دوال الأكواد ====================

def add_promo_code(code: str, max_uses: int, points: int) -> bool:
    """إضافة كود ترويجي"""
    try:
        execute_query(
            "INSERT INTO promo_codes (code, max_uses, points) VALUES (?, ?, ?)",
            (code, max_uses, points)
        )
        return True
    except Exception:
        return False

def use_promo_code(code: str, user_id: int) -> bool:
    """استخدام كود ترويجي"""
    try:
        # التحقق من الكود
        promo = execute_query(
            "SELECT * FROM promo_codes WHERE code = ? AND active = 1 AND used_count < max_uses",
            (code,),
            fetch_one=True
        )
        
        if not promo:
            return False
            
        # التحقق من الاستخدام السابق
        used = execute_query(
            "SELECT * FROM promo_uses WHERE code = ? AND user_id = ?",
            (code, user_id),
            fetch_one=True
        )
        
        if used:
            return False
            
        # تسجيل الاستخدام
        execute_query(
            "INSERT INTO promo_uses (code, user_id) VALUES (?, ?)",
            (code, user_id)
        )
        
        # تحديث عدد الاستخدامات
        execute_query(
            "UPDATE promo_codes SET used_count = used_count + 1 WHERE code = ?",
            (code,)
        )
        
        # إضافة النقاط
        add_points(user_id, promo["points"])
        
        return True
        
    except Exception:
        return False

# ==================== دوال المشرفين ====================

def add_supervisor(user_id: int, username: str = "") -> bool:
    """إضافة مشرف"""
    try:
        execute_query(
            "INSERT INTO supervisors (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        return True
    except Exception:
        return False

def remove_supervisor(user_id: int) -> bool:
    """إزالة مشرف"""
    try:
        execute_query("DELETE FROM supervisors WHERE user_id = ?", (user_id,))
        return True
    except Exception:
        return False

def get_supervisors() -> List[Dict[str, Any]]:
    """الحصول على قائمة المشرفين"""
    return execute_query("SELECT * FROM supervisors ORDER BY added_at DESC", fetch_all=True) or []

def is_supervisor(user_id: int) -> bool:
    """التحقق من صلاحية المشرف"""
    result = execute_query(
        "SELECT * FROM supervisors WHERE user_id = ?",
        (user_id,),
        fetch_one=True
    )
    return result is not None

def add_supervisor_account(supervisor_id: int, phone: str, session_string: str) -> bool:
    """إضافة حساب لمشرف"""
    try:
        execute_query(
            "INSERT INTO supervisor_accounts (supervisor_id, phone_number, session_string) VALUES (?, ?, ?)",
            (supervisor_id, phone, session_string)
        )
        return True
    except Exception:
        return False

def get_supervisor_accounts(supervisor_id: int) -> List[Dict[str, Any]]:
    """الحصول على حسابات المشرف"""
    return execute_query(
        "SELECT * FROM supervisor_accounts WHERE supervisor_id = ? ORDER BY added_at DESC",
        (supervisor_id,),
        fetch_all=True
    ) or []

def delete_supervisor_account(supervisor_id: int, phone: str) -> bool:
    """حذف حساب مشرف"""
    try:
        execute_query(
            "DELETE FROM supervisor_accounts WHERE supervisor_id = ? AND phone_number = ?",
            (supervisor_id, phone)
        )
        return True
    except Exception:
        return False

# ==================== دوال الإحالة ====================

def add_referral_task(label: str, bot_username: str, start_param: str, mandatory_channels: str = "", folder_link: str = "") -> int:
    """إضافة مهمة إحالة"""
    try:
        result = execute_query(
            """INSERT INTO referral_tasks 
               (label, bot_username, start_param, mandatory_channels, folder_link) 
               VALUES (?, ?, ?, ?, ?) RETURNING id""",
            (label, bot_username, start_param, mandatory_channels, folder_link),
            fetch_one=True
        )
        return result["id"] if result else 0
    except Exception:
        return 0

def get_referral_tasks(active_only: bool = True) -> List[Dict[str, Any]]:
    """الحصول على مهام الإحالة"""
    query = "SELECT * FROM referral_tasks"
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY created_at DESC"
    return execute_query(query, fetch_all=True) or []

def get_referral_task(task_id: int) -> Optional[Dict[str, Any]]:
    """الحصول على مهمة إحالة"""
    return execute_query(
        "SELECT * FROM referral_tasks WHERE id = ?",
        (task_id,),
        fetch_one=True
    )

def delete_referral_task(task_id: int) -> bool:
    """حذف مهمة إحالة"""
    try:
        execute_query("DELETE FROM referral_tasks WHERE id = ?", (task_id,))
        return True
    except Exception:
        return False

def toggle_referral_task(task_id: int) -> bool:
    """تبديل حالة مهمة الإحالة"""
    try:
        task = get_referral_task(task_id)
        if not task:
            return False
        new_active = 0 if task["active"] else 1
        execute_query(
            "UPDATE referral_tasks SET active = ? WHERE id = ?",
            (new_active, task_id)
        )
        return bool(new_active)
    except Exception:
        return False

def mark_referral_completion(task_id: int, stock_id: int, status: str, error_msg: str = None) -> bool:
    """تسجيل إكمال إحالة"""
    try:
        execute_query(
            """INSERT OR REPLACE INTO referral_completions 
               (task_id, stock_id, status, done_at, error_msg) 
               VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)""",
            (task_id, stock_id, status, error_msg)
        )
        return True
    except Exception:
        return False

def get_pending_numbers_for_task(task_id: int) -> List[Dict[str, Any]]:
    """الحصول على الأرقام المعلقة لمهمة"""
    try:
        return execute_query(
            """SELECT a.id, a.phone, a.session_string 
               FROM accounts a
               WHERE a.is_active = 1 AND a.deleted_at IS NULL 
               AND a.session_string IS NOT NULL
               AND a.id NOT IN (
                   SELECT stock_id FROM referral_completions 
                   WHERE task_id = ? AND status = 'done'
               )
               ORDER BY a.id ASC""",
            (task_id,),
            fetch_all=True
        ) or []
    except Exception:
        return []

# ==================== الإحصائيات ====================

def get_stats() -> Dict[str, Any]:
    """الحصول على إحصائيات البوت"""
    try:
        accounts = execute_query("SELECT COUNT(*) as count FROM accounts WHERE is_active = 1 AND deleted_at IS NULL", fetch_one=True)
        clips = execute_query("SELECT COUNT(*) as count FROM clips", fetch_one=True)
        groups = execute_query("SELECT COUNT(*) as count FROM groups WHERE is_active = 1", fetch_one=True)
        users = execute_query("SELECT COUNT(*) as count FROM users", fetch_one=True)
        orders = execute_query("SELECT COUNT(*) as count FROM orders", fetch_one=True)
        
        return {
            "accounts": accounts["count"] if accounts else 0,
            "clips": clips["count"] if clips else 0,
            "groups": groups["count"] if groups else 0,
            "users": users["count"] if users else 0,
            "orders": orders["count"] if orders else 0
        }
    except Exception:
        return {}

# ==================== التنظيف ====================

def cleanup_old_sessions(days: int = 30) -> bool:
    """تنظيف الجلسات القديمة"""
    try:
        execute_query(
            "DELETE FROM rotated_sessions WHERE rotated_date < datetime('now', '-' || ? || ' days')",
            (days,)
        )
        return True
    except Exception:
        return False

def cleanup_old_logs(days: int = 30) -> bool:
    """تنظيف سجل الإرسال القديم"""
    try:
        execute_query(
            "DELETE FROM sent_log WHERE sent_date < datetime('now', '-' || ? || ' days')",
            (days,)
        )
        return True
    except Exception:
        return False

# ==================== التهيئة عند التشغيل ====================

# تهيئة قاعدة البيانات عند استيراد الملف
init_db()

logger.info("✅ تم تحميل وحدة قاعدة البيانات")
