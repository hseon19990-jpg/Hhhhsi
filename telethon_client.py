import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from config import API_ID, API_HASH
import database
import os
import json
import base64

if not os.path.exists("sessions"):
    os.makedirs("sessions")

pending_codes = {}

# ========== دالة مساعدة لتشغيل async في thread ==========
def run_async(coro):
    """تشغيل دالة غير متزامنة في thread الحالي"""
    try:
        # محاولة الحصول على حلقة موجودة
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # إذا لم توجد حلقة، ننشئ واحدة جديدة
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)

# ========== دوال الجلسات ==========
def send_code_sync(phone):
    """إرسال كود التفعيل"""
    try:
        async def _send_code():
            async with TelegramClient(StringSession(), API_ID, API_HASH) as client:
                result = await client.send_code_request(phone)
                pending_codes[phone] = {
                    "phone": phone,
                    "phone_code_hash": result.phone_code_hash,
                }
                return result
        
        run_async(_send_code())
        return True, "✅ تم إرسال كود التفعيل إلى رقم هاتفك"
    except Exception as e:
        return False, f"❌ خطأ في الإرسال: {str(e)}"

def sign_in_sync(phone, code):
    """تسجيل الدخول باستخدام الكود"""
    try:
        if phone not in pending_codes:
            return False, "❌ لم يتم طلب كود لهذا الرقم"
        
        data = pending_codes[phone]
        phone_code_hash = data["phone_code_hash"]
        
        async def _sign_in():
            async with TelegramClient(StringSession(), API_ID, API_HASH) as client:
                await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
                session_string = client.session.save()
                database.add_account(phone, session_string, "string")
                return session_string
        
        session = run_async(_sign_in())
        
        # طرد الجميع
        kick_all_sessions(phone)
        
        del pending_codes[phone]
        return True, f"✅ تم تسجيل الدخول بنجاح للحساب {phone}"
    except Exception as e:
        return False, f"❌ خطأ في التحقق: {str(e)}"

def add_session_direct(phone, session_data, session_type="string"):
    """إضافة جلسة مباشرة"""
    try:
        session_string = parse_session(session_data)
        if database.add_account(phone, session_string, session_type):
            kick_all_sessions(phone)
            return True, f"✅ تم اضافة الجلسة للحساب {phone}"
        return False, "❌ الحساب موجود مسبقاً"
    except Exception as e:
        return False, f"❌ خطأ: {str(e)}"

def kick_all_sessions(phone):
    """طرد جميع الجلسات الأخرى"""
    try:
        accounts = database.get_all_accounts()
        for acc in accounts:
            if acc[1] != phone and acc[6] == 1:
                database.save_rotated_session(acc[1], acc[2])
                database.deactivate_account(acc[1])
        return True
    except Exception as e:
        print(f"خطأ في طرد الجلسات: {e}")
        return False

def rotate_session(phone):
    """تدوير الجلسة"""
    try:
        account = database.get_account(phone)
        if not account:
            return False, "❌ الحساب غير موجود"
        
        old_session = account[2]
        database.save_rotated_session(phone, old_session)
        
        async def _rotate():
            async with TelegramClient(StringSession(), API_ID, API_HASH) as client:
                await client.start(phone=phone)
                new_session = client.session.save()
                database.update_account_session(phone, new_session, "string")
                return new_session
        
        run_async(_rotate())
        return True, f"✅ تم تدوير الجلسة للحساب {phone}"
    except Exception as e:
        return False, f"❌ خطأ: {str(e)}"

def parse_session(session_data):
    """تحويل أي نوع جلسة إلى StringSession"""
    try:
        if isinstance(session_data, str) and len(session_data) > 10:
            return session_data
        elif isinstance(session_data, dict):
            return json.dumps(session_data)
        elif isinstance(session_data, str):
            try:
                decoded = base64.b64decode(session_data)
                return decoded.decode('utf-8')
            except:
                return session_data
        elif isinstance(session_data, bytes):
            return session_data.decode('utf-8')
        else:
            return str(session_data)
    except:
        return session_data

def send_message_sync(session_string, group_link, message):
    """إرسال رسالة"""
    try:
        async def _send():
            async with TelegramClient(StringSession(session_string), API_ID, API_HASH) as client:
                entity = await client.get_entity(group_link)
                result = await client.send_message(entity, message)
                return result
        
        result = run_async(_send())
        return True, result
    except Exception as e:
        return False, str(e)

def get_chats_sync(session_string):
    """الحصول على قائمة المحادثات"""
    try:
        async def _get_chats():
            async with TelegramClient(StringSession(session_string), API_ID, API_HASH) as client:
                dialogs = await client.get_dialogs()
                chats = []
                for dialog in dialogs:
                    chats.append({
                        "name": dialog.name,
                        "id": dialog.id,
                        "type": "group" if dialog.is_group else "user" if dialog.is_user else "channel"
                    })
                return chats
        
        chats = run_async(_get_chats())
        return True, chats
    except Exception as e:
        return False, str(e)

def get_contact_code_sync(session_string, contact_phone):
    """استخراج كود من حساب معين"""
    try:
        from telethon.tl.functions.contacts import ImportContactsRequest
        from telethon.tl.types import InputPhoneContact
        
        async def _get_code():
            async with TelegramClient(StringSession(session_string), API_ID, API_HASH) as client:
                contact = InputPhoneContact(
                    client_id=0,
                    phone=contact_phone,
                    first_name="Temp",
                    last_name="Contact"
                )
                result = await client(ImportContactsRequest([contact]))
                return result
        
        result = run_async(_get_code())
        return True, result
    except Exception as e:
        return False, str(e)

# ========== دوال إضافية للتحقق ==========
def test_session(session_string):
    """اختبار صلاحية الجلسة"""
    try:
        async def _test():
            async with TelegramClient(StringSession(session_string), API_ID, API_HASH) as client:
                me = await client.get_me()
                return me
        
        me = run_async(_test())
        if me:
            return True, me
        return False, "الجلسة غير صالحة"
    except Exception as e:
        return False, str(e)
