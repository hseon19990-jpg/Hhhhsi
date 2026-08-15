import telebot
from telebot import types
import logging
from config import BOT_TOKEN
import database
import states
import scheduler
from telethon_client import send_code_sync, sign_in_sync

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN)

# تهيئة قاعدة البيانات
database.init_db()

# بدء المؤقت
scheduler.start_scheduler()

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
        types.KeyboardButton("📊 الاحصائيات")
    )
    return markup

# ========== أمر start ==========
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "🤖 اهلاً بك في بوت سننشا!\n\n"
        "📌 بوت لنشر الكليشات تلقائياً عبر حسابات متعددة\n"
        "⚡ كل حساب يرسل 50 رسالة يومياً\n\n"
        "اختر أحد الأزرار:",
        reply_markup=main_menu()
    )

# ========== معالجة الأزرار ==========
@bot.message_handler(func=lambda msg: True)
def handle_buttons(message):
    user_id = message.chat.id
    text = message.text
    current_state = states.get_state(user_id)
    
    # ===== معالجة الحالات =====
    if current_state == states.STATE_WAITING_ACCOUNT:
        phone = text.strip()
        if phone.isdigit() and len(phone) >= 10:
            success, msg = send_code_sync(phone)
            if success:
                states.set_temp_data(user_id, "phone", phone)
                states.set_state(user_id, states.STATE_WAITING_CONFIRM)
                bot.reply_to(message, f"📱 {msg}\n\n✏️ ارسل الكود الذي وصلك:")
            else:
                bot.reply_to(message, f"❌ {msg}")
        else:
            bot.reply_to(message, "❌ رقم هاتف غير صحيح\nأرسل رقم مع مفتاح الدولة (مثال: 9647812345678)")
        return
    
    elif current_state == states.STATE_WAITING_CONFIRM:
        code = text.strip()
        phone = states.get_temp_data(user_id, "phone")
        if phone and code:
            success, msg = sign_in_sync(phone, code)
            if success:
                bot.reply_to(message, f"✅ {msg}")
                logger.info(f"تم اضافة حساب: {phone}")
            else:
                bot.reply_to(message, f"❌ {msg}")
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
            bot.reply_to(message, "❌ رابط غير صحيح")
        states.clear_state(user_id)
        return
    
    elif current_state == states.STATE_WAITING_DELETE_ACCOUNT:
        accounts = database.get_accounts()
        try:
            index = int(text) - 1
            if 0 <= index < len(accounts):
                phone = accounts[index][1]
                database.delete_account(phone)
                bot.reply_to(message, f"✅ تم حذف الحساب: {phone}")
            else:
                bot.reply_to(message, "❌ رقم غير صحيح")
        except:
            bot.reply_to(message, "❌ يرجى ارسال رقم")
        states.clear_state(user_id)
        return
    
    elif current_state == states.STATE_WAITING_DELETE_GROUP:
        groups = database.get_groups()
        try:
            index = int(text) - 1
            if 0 <= index < len(groups):
                group_link = groups[index][1]
                database.delete_group(group_link)
                bot.reply_to(message, f"✅ تم حذف الكروب: {group_link}")
            else:
                bot.reply_to(message, "❌ رقم غير صحيح")
        except:
            bot.reply_to(message, "❌ يرجى ارسال رقم")
        states.clear_state(user_id)
        return
    
    elif current_state == states.STATE_WAITING_DELETE_CLIP:
        try:
            clip_id = int(text)
            database.delete_clip(clip_id)
            bot.reply_to(message, f"✅ تم حذف الكليشة رقم {clip_id}")
        except:
            bot.reply_to(message, "❌ يرجى ارسال رقم صحيح")
        states.clear_state(user_id)
        return
    
    elif current_state == states.STATE_WAITING_TIMER:
        success, msg = scheduler.set_timer(text)
        bot.reply_to(message, msg)
        states.clear_state(user_id)
        return
    
    # ===== الأزرار الرئيسية =====
    if text == "➕ اضافة حساب":
        states.set_state(user_id, states.STATE_WAITING_ACCOUNT)
        bot.reply_to(message, "📱 ارسل رقم الهاتف مع مفتاح الدولة\nمثال: 9647812345678")
    
    elif text == "📝 اضافة كليشة":
        states.set_state(user_id, states.STATE_WAITING_CLIP)
        bot.reply_to(message, "✏️ ارسل الكليشات (كل سطر = كليشة)\nمثال:\nعاش العراق\nمحمد قوي")
    
    elif text == "👥 اضافة كروب":
        states.set_state(user_id, states.STATE_WAITING_GROUP)
        bot.reply_to(message, "🔗 ارسل رابط الكروب\nمثال: https://t.me/groupname")
    
    elif text == "❌ حذف حساب":
        accounts = database.get_accounts()
        if accounts:
            msg = "🗑️ *اختر الحساب للحذف:*\n\n"
            for i, acc in enumerate(accounts, 1):
                msg += f"{i}. {acc[1]}\n"
            bot.reply_to(message, msg, parse_mode='Markdown')
            states.set_state(user_id, states.STATE_WAITING_DELETE_ACCOUNT)
        else:
            bot.reply_to(message, "❌ لا يوجد حسابات")
    
    elif text == "🚫 حذف كروب":
        groups = database.get_groups()
        if groups:
            msg = "🗑️ *اختر الكروب للحذف:*\n\n"
            for i, grp in enumerate(groups, 1):
                msg += f"{i}. {grp[1]}\n"
            bot.reply_to(message, msg, parse_mode='Markdown')
            states.set_state(user_id, states.STATE_WAITING_DELETE_GROUP)
        else:
            bot.reply_to(message, "❌ لا يوجد كروبات")
    
    elif text == "🗑️ حذف كليشة":
        clips = database.get_clips()
        if clips:
            msg = "🗑️ *اختر الكليشة للحذف (ارسل الرقم):*\n\n"
            for clip in clips[:10]:
                preview = clip[1][:30] + "..." if len(clip[1]) > 30 else clip[1]
                msg += f"{clip[0]}: {preview}\n"
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
        bot.reply_to(message, f"⏰ المؤقت الحالي: {current} ثانية\nارسل الوقت الجديد")
    
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
        bot.reply_to(message, "❌ استخدم الأزرار")

# ========== تشغيل البوت ==========
if __name__ == "__main__":
    print("🤖 البوت يعمل...")
    bot.infinity_polling()
