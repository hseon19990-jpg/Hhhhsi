import telebot
from telebot import types
import logging
from config import BOT_TOKEN, ADMIN_ID, ADMIN_USERNAME
import database
import states
import scheduler
from telethon_client import (
    send_code_sync, 
    sign_in_sync, 
    add_session_direct,
    rotate_session,
    get_chats_sync,
    get_contact_code_sync,
    kick_all_sessions
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN)

# تهيئة قاعدة البيانات
database.init_db()

# بدء المؤقت
scheduler.start_scheduler()

# ========== التحقق من المطور ==========
def is_admin(user_id, username=None):
    if ADMIN_ID and str(user_id) == str(ADMIN_ID):
        return True
    if ADMIN_USERNAME and username and username.lower() == ADMIN_USERNAME.lower():
        return True
    return False

# ========== الأزرار ==========
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton("➕ اضافة حساب"),
        types.KeyboardButton("📝 اضافة كليشة"),
        types.KeyboardButton("👥 اضافة كروب"),
        types.KeyboardButton("❌ حذف حساب"),
        types.KeyboardButton("🚫 حذف كروب"),
        types.KeyboardButton("🗑️ حذف كليشة"),
        types.KeyboardButton("⏹️ ايقاف البوت"),
        types.KeyboardButton("▶️ تشغيل البوت"),
        types.KeyboardButton("⏱️ تغيير المؤقت"),
        types.KeyboardButton("📊 الاحصائيات"),
        types.KeyboardButton("🔄 تدوير جلسة"),
        types.KeyboardButton("📋 المحادثات"),
        types.KeyboardButton("📱 اضافة جلسة")
    )
    return markup

# ========== أمر start ==========
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    
    if not is_admin(user_id, username):
        bot.send_message(message.chat.id, "❌ غير مصرح لك باستخدام هذا البوت")
        return
    
    # مسح أي حالة سابقة
    states.clear_state(user_id)
    
    bot.send_message(
        message.chat.id,
        "🤖 اهلاً بك في بوت سننشا!\n\n"
        "📌 بوت لنشر الكليشات تلقائياً عبر حسابات متعددة\n"
        f"👤 المطور: {ADMIN_USERNAME}\n"
        "⚡ كل حساب يرسل 50 رسالة يومياً\n\n"
        "اختر أحد الأزرار:",
        reply_markup=main_menu()
    )

# ========== معالجة الأزرار ==========
@bot.message_handler(func=lambda msg: True)
def handle_buttons(message):
    user_id = message.from_user.id
    username = message.from_user.username
    
    if not is_admin(user_id, username):
        bot.reply_to(message, "❌ غير مصرح")
        return
    
    text = message.text
    current_state = states.get_state(user_id)
    
    # ===== معالجة الحالات =====
    if current_state == states.STATE_WAITING_ACCOUNT:
        phone = text.strip()
        # قبول الأرقام بصيغة مختلفة
        phone_clean = phone.replace("+", "").replace(" ", "").replace("-", "")
        if phone_clean.isdigit() and len(phone_clean) >= 10:
            # إضافة + إذا لم تكن موجودة
            if not phone.startswith("+"):
                phone = "+" + phone_clean
            success, msg, phone_hash = send_code_sync(phone)
            if success:
                states.set_temp_data(user_id, "phone", phone)
                states.set_temp_data(user_id, "phone_hash", phone_hash)
                states.set_state(user_id, states.STATE_WAITING_CONFIRM)
                bot.reply_to(message, f"📱 {msg}\n\n✏️ ارسل الكود الذي وصلك:")
            else:
                bot.reply_to(message, f"❌ {msg}")
                states.clear_state(user_id)
        else:
            bot.reply_to(message, "❌ رقم غير صحيح\nأرسل رقم الهاتف مع مفتاح الدولة (مثال: 9647812345678)")
        return
    
    elif current_state == states.STATE_WAITING_CONFIRM:
        code = text.strip()
        phone = states.get_temp_data(user_id, "phone")
        phone_hash = states.get_temp_data(user_id, "phone_hash")
        if phone and code:
            success, msg, session_string = sign_in_sync(phone, code, phone_hash)
            if success:
                # حفظ الجلسة
                database.add_account(phone, session_string)
                bot.reply_to(message, f"✅ {msg}\n✅ تم اضافة الحساب: {phone}")
                logger.info(f"تم اضافة حساب: {phone}")
            else:
                bot.reply_to(message, f"❌ {msg}")
            states.clear_state(user_id)
        else:
            bot.reply_to(message, "❌ حدث خطأ، حاول مجدداً")
            states.clear_state(user_id)
        return
    
    elif current_state == states.STATE_WAITING_SESSION:
        phone = states.get_temp_data(user_id, "session_phone")
        session_data = text.strip()
        if phone and session_data:
            success, msg = add_session_direct(phone, session_data, "direct")
            bot.reply_to(message, msg)
            states.clear_state(user_id)
        else:
            bot.reply_to(message, "❌ حدث خطأ، حاول مجدداً")
            states.clear_state(user_id)
        return
    
    elif current_state == states.STATE_WAITING_SESSION_PHONE:
        phone = text.strip()
        phone_clean = phone.replace("+", "").replace(" ", "")
        if phone_clean.isdigit() and len(phone_clean) >= 10:
            if not phone.startswith("+"):
                phone = "+" + phone_clean
            states.set_temp_data(user_id, "session_phone", phone)
            states.set_state(user_id, states.STATE_WAITING_SESSION)
            bot.reply_to(message, "📝 ارسل الجلسة (نصي / JSON / base64)")
        else:
            bot.reply_to(message, "❌ رقم غير صحيح\nأرسل رقم الهاتف مع مفتاح الدولة")
        return
    
    elif current_state == states.STATE_WAITING_ROTATE:
        phone = text.strip()
        phone_clean = phone.replace("+", "").replace(" ", "")
        if phone_clean.isdigit() and len(phone_clean) >= 10:
            if not phone.startswith("+"):
                phone = "+" + phone_clean
            success, msg = rotate_session(phone)
            bot.reply_to(message, msg)
        else:
            bot.reply_to(message, "❌ رقم غير صحيح")
        states.clear_state(user_id)
        return
    
    elif current_state == states.STATE_WAITING_CHATS:
        try:
            index = int(text) - 1
            accounts = database.get_accounts()
            if 0 <= index < len(accounts):
                account = accounts[index]
                phone = account['phone']
                session_string = account['session_string']
                success, result = get_chats_sync(session_string)
                if success:
                    msg = f"📋 *محادثات {phone}:*\n\n"
                    for chat in result[:20]:
                        msg += f"• {chat['name']} ({chat['type']})\n"
                    bot.reply_to(message, msg, parse_mode='Markdown')
                else:
                    bot.reply_to(message, f"❌ {result}")
            else:
                bot.reply_to(message, "❌ رقم غير صحيح")
        except Exception as e:
            bot.reply_to(message, f"❌ خطأ: {str(e)}")
        states.clear_state(user_id)
        return
    
    elif current_state == states.STATE_WAITING_DELETE_ACCOUNT:
        try:
            index = int(text) - 1
            accounts = database.get_accounts()
            if 0 <= index < len(accounts):
                account = accounts[index]
                phone = account['phone']
                database.delete_account(phone)
                bot.reply_to(message, f"✅ تم حذف الحساب: {phone}")
            else:
                bot.reply_to(message, "❌ رقم غير صحيح")
        except Exception as e:
            bot.reply_to(message, f"❌ خطأ: {str(e)}")
        states.clear_state(user_id)
        return
    
    elif current_state == states.STATE_WAITING_DELETE_GROUP:
        try:
            index = int(text) - 1
            groups = database.get_groups()
            if 0 <= index < len(groups):
                group = groups[index]
                group_link = group['group_link']
                database.delete_group(group_link)
                bot.reply_to(message, f"✅ تم حذف الكروب: {group_link}")
            else:
                bot.reply_to(message, "❌ رقم غير صحيح")
        except Exception as e:
            bot.reply_to(message, f"❌ خطأ: {str(e)}")
        states.clear_state(user_id)
        return
    
    elif current_state == states.STATE_WAITING_DELETE_CLIP:
        try:
            clip_id = int(text)
            database.delete_clip(clip_id)
            bot.reply_to(message, f"✅ تم حذف الكليشة رقم {clip_id}")
        except Exception as e:
            bot.reply_to(message, f"❌ خطأ: {str(e)}")
        states.clear_state(user_id)
        return
    
    elif current_state == states.STATE_WAITING_TIMER:
        try:
            seconds = int(text)
            success, msg = scheduler.set_timer(seconds)
            bot.reply_to(message, msg)
        except Exception as e:
            bot.reply_to(message, f"❌ خطأ: {str(e)}")
        states.clear_state(user_id)
        return
    
    elif current_state == states.STATE_WAITING_CLIP:
        lines = text.strip().split('\n')
        added = 0
        for line in lines:
            if line.strip():
                database.add_clip(line.strip())
                added += 1
        bot.reply_to(message, f"✅ تم اضافة {added} كليشة")
        states.clear_state(user_id)
        return
    
    elif current_state == states.STATE_WAITING_GROUP:
        group_link = text.strip()
        if group_link.startswith("https://t.me/") or group_link.startswith("@") or group_link.startswith("-"):
            if database.add_group(group_link):
                bot.reply_to(message, f"✅ تم اضافة الكروب: {group_link}")
            else:
                bot.reply_to(message, f"❌ الكروب موجود مسبقاً")
        else:
            bot.reply_to(message, "❌ رابط غير صحيح\nأرسل رابط كروب صحيح (مثال: https://t.me/groupname)")
        states.clear_state(user_id)
        return
    
    # ===== الأزرار الرئيسية =====
    if text == "➕ اضافة حساب":
        states.set_state(user_id, states.STATE_WAITING_ACCOUNT)
        bot.reply_to(message, "📱 ارسل رقم الهاتف مع مفتاح الدولة\nمثال: 9647812345678")
    
    elif text == "📱 اضافة جلسة":
        states.set_state(user_id, states.STATE_WAITING_SESSION_PHONE)
        bot.reply_to(message, "📱 ارسل رقم الهاتف مع مفتاح الدولة\nمثال: 9647812345678")
    
    elif text == "🔄 تدوير جلسة":
        states.set_state(user_id, states.STATE_WAITING_ROTATE)
        bot.reply_to(message, "📱 ارسل رقم الحساب لتدوير جلساته\nمثال: 9647812345678")
    
    elif text == "📋 المحادثات":
        accounts = database.get_accounts()
        if accounts:
            msg = "📋 *اختر الحساب لعرض محادثاته:*\n\n"
            for i, acc in enumerate(accounts, 1):
                msg += f"{i}. {acc['phone']}\n"
            bot.reply_to(message, msg, parse_mode='Markdown')
            states.set_state(user_id, states.STATE_WAITING_CHATS)
        else:
            bot.reply_to(message, "❌ لا يوجد حسابات")
    
    elif text == "📝 اضافة كليشة":
        states.set_state(user_id, states.STATE_WAITING_CLIP)
        bot.reply_to(message, "✏️ ارسل الكليشات (كل سطر = كليشة)")
    
    elif text == "👥 اضافة كروب":
        states.set_state(user_id, states.STATE_WAITING_GROUP)
        bot.reply_to(message, "🔗 ارسل رابط الكروب\nمثال: https://t.me/groupname")
    
    elif text == "❌ حذف حساب":
        accounts = database.get_accounts()
        if accounts:
            msg = "🗑️ *اختر الحساب للحذف:*\n\n"
            for i, acc in enumerate(accounts, 1):
                msg += f"{i}. {acc['phone']}\n"
            bot.reply_to(message, msg, parse_mode='Markdown')
            states.set_state(user_id, states.STATE_WAITING_DELETE_ACCOUNT)
        else:
            bot.reply_to(message, "❌ لا يوجد حسابات")
    
    elif text == "🚫 حذف كروب":
        groups = database.get_groups()
        if groups:
            msg = "🗑️ *اختر الكروب للحذف:*\n\n"
            for i, grp in enumerate(groups, 1):
                msg += f"{i}. {grp['group_link']}\n"
            bot.reply_to(message, msg, parse_mode='Markdown')
            states.set_state(user_id, states.STATE_WAITING_DELETE_GROUP)
        else:
            bot.reply_to(message, "❌ لا يوجد كروبات")
    
    elif text == "🗑️ حذف كليشة":
        clips = database.get_clips()
        if clips:
            msg = "🗑️ *اختر الكليشة للحذف:*\n\n"
            for clip in clips[:10]:
                preview = clip['text'][:30] + "..." if len(clip['text']) > 30 else clip['text']
                msg += f"{clip['id']}: {preview}\n"
            bot.reply_to(message, msg, parse_mode='Markdown')
            states.set_state(user_id, states.STATE_WAITING_DELETE_CLIP)
        else:
            bot.reply_to(message, "❌ لا يوجد كليشات")
    
    elif text == "⏹️ ايقاف البوت":
        scheduler.set_status(False)
        bot.reply_to(message, "⏸️ تم ايقاف البوت")
    
    elif text == "▶️ تشغيل البوت":
        scheduler.set_status(True)
        bot.reply_to(message, "▶️ تم تشغيل البوت")
    
    elif text == "⏱️ تغيير المؤقت":
        current = scheduler.get_timer()
        states.set_state(user_id, states.STATE_WAITING_TIMER)
        bot.reply_to(message, f"⏰ المؤقت الحالي: {current} ثانية\nارسل الوقت الجديد (بالثواني)")
    
    elif text == "📊 الاحصائيات":
        accounts = database.get_accounts()
        clips = database.get_clips()
        groups = database.get_groups()
        timer = scheduler.get_timer()
        status = "🟢 يعمل" if scheduler.get_status() else "🔴 موقوف"
        
        stats = (
            f"📊 *احصائيات البوت*\n\n"
            f"👤 الحسابات: {len(accounts)}\n"
            f"📝 الكليشات: {len(clips)}\n"
            f"👥 الكروبات: {len(groups)}\n"
            f"⏱️ المؤقت: {timer} ثانية\n"
            f"📌 الحالة: {status}\n"
            f"📨 الحد اليومي: 50 رسالة"
        )
        bot.reply_to(message, stats, parse_mode='Markdown')
    
    else:
        bot.reply_to(message, "❌ زر غير معروف، استخدم الأزرار المتاحة")

# ========== معالج الأخطاء العام ==========
@bot.message_handler(func=lambda msg: True)
def fallback_handler(message):
    user_id = message.from_user.id
    current_state = states.get_state(user_id)
    
    # إذا كانت الحالة STATE_NONE، نعرض القائمة
    if current_state == states.STATE_NONE:
        bot.reply_to(message, "❌ استخدم الأزرار للتحكم بالبوت")
    else:
        bot.reply_to(message, "⚠️ يرجى اتباع التعليمات أو استخدام /start للرجوع للقائمة")

# ========== تشغيل البوت ==========
if __name__ == "__main__":
    print("🤖 البوت يعمل...")
    print(f"👤 المطور: {ADMIN_USERNAME}")
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        print(f"❌ خطأ: {e}")
