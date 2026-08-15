from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import InputPhoneContact
from telethon.tl.functions.contacts import ImportContactsRequest
from config import API_ID, API_HASH
import database
import os
import json
import base64

if not os.path.exists("sessions"):
    os.makedirs("sessions")

pending_codes = {}

# ========== دالة استقبال أي نوع جلسة ==========
def parse_session(session_data):
    """تحويل أي نوع جلسة إلى StringSession"""
    try:
        # إذا كانت جلسة نصية عادية
        if isinstance(session_data, str) and len(session_data) > 10:
            return session_data
        
        # إذا كانت JSON
        elif isinstance(session_data, dict):
            return json.dumps(session_data)
        
        # إذا كانت base64
        elif isinstance(session_data, str):
            try:
                decoded = base64.b64decode(session_data)
                return decoded.decode('utf-8')
            except:
                return session_data
        
        # إذا كانت bytes
        elif isinstance(session_data, bytes):
            return session_data.decode('utf-8')
        
        else:
            return str(session_data)
    except:
        return session_data

# ========== دوال الجلسات ==========
def send_code_sync(phone):
    try:
        with TelegramClient(StringSession(), API_ID, API_HASH) as client:
            result = client.send_code_request(phone)
            pending_codes[phone] = {
                "phone": phone,
                "phone_code_hash": result.phone_code_hash,
                "client_session": client.session.save()
            }
            return True, "✅ تم إرسال كود التفعيل"
    except Exception as e:
        return False, f"❌ خطأ: {str(e)}"

def sign_in_sync(phone, code):
    try:
        if phone not in pending_codes:
            return False, "❌ لم يتم طلب كود"
        
        data = pending_codes[phone]
        phone_code_hash = data["phone_code_hash"]
        
        with TelegramClient(StringSession(), API_ID, API_HASH) as client:
            client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            session_string = client.session.save()
            
            # إضافة الحساب مع نوع الجلسة
            database.add_account(phone, session_string, "string")
        
        # طرد جميع الجلسات الأخرى (تدوير)
        kick_all_sessions(phone)
        
        del pending_codes[phone]
        return True, f"✅ تم تسجيل الدخول للحساب {phone}"
    except Exception as e:
        return False, f"❌ خطأ: {str(e)}"

def add_session_direct(phone, session_data, session_type="string"):
    """إضافة جلسة مباشرة (أي نوع)"""
    try:
        session_string = parse_session(session_data)
        if database.add_account(phone, session_string, session_type):
            # طرد جميع الجلسات الأخرى
            kick_all_sessions(phone)
            return True, f"✅ تم اضافة الجلسة للحساب {phone}"
        return False, "❌ الحساب موجود مسبقاً"
    except Exception as e:
        return False, f"❌ خطأ: {str(e)}"

def kick_all_sessions(phone):
    """طرد جميع الجلسات الأخرى لنفس الرقم"""
    try:
        accounts = database.get_all_accounts()
        for acc in accounts:
            if acc[1] != phone and acc[6] == 1:  # is_active = 1
                # حفظ الجلسة القديمة كمدورة
                database.save_rotated_session(acc[1], acc[2])
                # تعطيل الحساب
                database.deactivate_account(acc[1])
        return True
    except Exception as e:
        print(f"خطأ في طرد الجلسات: {e}")
        return False

def rotate_session(phone):
    """تدوير الجلسة (إنشاء جلسة جديدة)"""
    try:
        account = database.get_account(phone)
        if not account:
            return False, "❌ الحساب غير موجود"
        
        old_session = account[2]
        
        # حفظ الجلسة القديمة
        database.save_rotated_session(phone, old_session)
        
        # إنشاء جلسة جديدة
        with TelegramClient(StringSession(), API_ID, API_HASH) as client:
            client.start(phone=phone)
            new_session = client.session.save()
            database.update_account_session(phone, new_session, "string")
        
        return True, f"✅ تم تدوير الجلسة للحساب {phone}"
    except Exception as e:
        return False, f"❌ خطأ: {str(e)}"

def send_message_sync(session_string, group_link, message):
    try:
        with TelegramClient(StringSession(session_string), API_ID, API_HASH) as client:
            entity = client.get_entity(group_link)
            result = client.send_message(entity, message)
            return True, result
    except Exception as e:
        return False, str(e)

def get_chats_sync(session_string):
    """الحصول على قائمة المحادثات من الحساب"""
    try:
        with TelegramClient(StringSession(session_string), API_ID, API_HASH) as client:
            dialogs = client.get_dialogs()
            chats = []
            for dialog in dialogs:
                chats.append({
                    "name": dialog.name,
                    "id": dialog.id,
                    "type": "group" if dialog.is_group else "user" if dialog.is_user else "channel"
                })
            return True, chats
    except Exception as e:
        return False, str(e)

def get_contact_code_sync(session_string, contact_phone):
    """استخراج كود من حساب معين"""
    try:
        with TelegramClient(StringSession(session_string), API_ID, API_HASH) as client:
            # إضافة جهة اتصال
            contact = InputPhoneContact(
                client_id=0,
                phone=contact_phone,
                first_name="Temp",
                last_name="Contact"
            )
            result = client(ImportContactsRequest([contact]))
            return True, result
    except Exception as e:
        return False, str(e)
