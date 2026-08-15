import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from config import API_ID, API_HASH
import database
import os

# مجلد الجلسات
if not os.path.exists("sessions"):
    os.makedirs("sessions")

# تخزين مؤقت للكودات
pending_codes = {}

def send_code_sync(phone):
    """إرسال كود التفعيل إلى رقم الهاتف (نسخة متزامنة)"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        loop.run_until_complete(client.connect())
        result = loop.run_until_complete(client.send_code_request(phone))
        
        pending_codes[phone] = {
            "phone": phone,
            "phone_code_hash": result.phone_code_hash,
            "client": client
        }
        
        loop.close()
        return True, "✅ تم إرسال كود التفعيل إلى رقم هاتفك"
    except Exception as e:
        return False, f"❌ خطأ في الإرسال: {str(e)}"

def sign_in_sync(phone, code):
    """تسجيل الدخول باستخدام الكود (نسخة متزامنة)"""
    try:
        if phone not in pending_codes:
            return False, "❌ لم يتم طلب كود لهذا الرقم"
        
        data = pending_codes[phone]
        client = data["client"]
        phone_code_hash = data["phone_code_hash"]
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # محاولة تسجيل الدخول
        await_sign = client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        loop.run_until_complete(await_sign)
        
        # حفظ الجلسة
        session_string = client.session.save()
        database.add_account(phone, session_string)
        
        # تنظيف
        del pending_codes[phone]
        loop.close()
        
        return True, f"✅ تم تسجيل الدخول بنجاح للحساب {phone}"
    except Exception as e:
        return False, f"❌ خطأ في التحقق: {str(e)}"

def send_message_sync(session_string, group_link, message):
    """إرسال رسالة إلى كروب باستخدام الجلسة"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        loop.run_until_complete(client.connect())
        
        # الحصول على الكيان
        entity = loop.run_until_complete(client.get_entity(group_link))
        
        # إرسال الرسالة
        result = loop.run_until_complete(client.send_message(entity, message))
        
        loop.close()
        return True, result
    except Exception as e:
        return False, str(e)
