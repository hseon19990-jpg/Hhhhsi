import telebot
from telebot import types
import logging
import time
import threading
from config import BOT_TOKEN
import database
import states
import scheduler

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
        # استقبال رقم الهاتف
        phone = text.strip()
        if phone.isdigit() and len(phone) >= 10:
            states.set_temp_data(user_id, "phone", phone)
            states.set_state(user_id, states.STATE_WAITING_CONFIRM)
            bot.reply_to(message, f"📱 تم استقبال الرقم: {phone}\n\nارسل كود التفعيل من تليجرام:")
        else:
            bot.reply_to(message, "❌ رقم هاتف غير صحيح\nأرسل رقم مع مفتاح الدولة (مثال: 9647812345678)")
        return
    
    elif current_state == states.STATE_WAITING_CONFIRM:
        # استقبال كود التفعيل
        code = text.strip()
        phone = states.get_temp_data(user_id, "phone")
        if phone and code:
            # هنا ستضيف كود تسجيل الدخول باستخدام Telethon
            # حالياً نقوم بمحاكاة التسجيل
            session_string = f"session_{phone}_{code}"  # مؤقت
            if database.add_account(phone, session_string):
                bot.reply_to(message, f"✅ تم اضافة الحساب: {phone}\n🔄 جارٍ تسجيل الدخول...")
                logger.info(f"تم اضافة حساب: {phone}")
            else:
                bot.reply_to(message, f"❌ الحساب {phone} موجود مسبقاً")
            states.clear_state(user_id)
        return
    
    elif current_state == states.STATE_WAITING_CLIP:
        # استقبال الكليشات (كل سطر = كليشة)
        lines = text.strip().split('\n')
        added = 0
        for line in lines:
            if line.strip():
                database.add_clip(line.strip())
                added += 1
        bot.reply_to(message, f"✅ تم اضافة {added} كليشة بنجاح")
        states.clear_state(user_id)
        return
    
    elif current_state == states.STATE_WAITING_GROUP:
        # استقبال رابط الكروب
        group_link = text.strip()
        if group_link.startswith("https://t.me/") or group_link.startswith("@") or group_link.startswith("-"):
            if database.add_group(group_link):
                bot.reply_to(message, f"✅ تم اضافة الكروب: {group_link}")
                logger.info(f"تم اضافة كروب: {group_link}")
            else:
                bot.reply_to(message, f"❌ الكروب {group_link} موجود مسبقاً")
        else:
            bot.reply_to(message, "❌ رابط غير صحيح\nأرسل رابط كروب صحيح (مثال: https://t.me/groupname)")
        states.clear_state(user_id)
        return
    
    elif current_state == states.STATE_WAITING_DELETE_ACCOUNT:
        # حذف حساب
        accounts = database.get_accounts()
        try:
            index = int(text) - 1
            if 0 <= index < len(accounts):
                phone = accounts[index][1]
                database.delete_account(phone)
                bot.reply_to(message, f"✅ تم حذف الحساب: {phone}")
                logger.info(f"تم حذف حساب: {phone}")
            else:
                bot.reply_to(message, "❌ رقم غير صحيح")
        except:
            bot.reply_to(message, "❌ يرجى ارسال رقم صحيح")
        states.clear_state(user_id)
        return
    
    elif current_state == states.STATE_WAITING_DELETE_GROUP:
        # حذف كروب
        groups = database.get_groups()
        try:
            index = int(text) - 1
            if 0 <= index < len(groups):
                group_link = groups[index][1]
                database.delete_group(group_link)
                bot.reply_to(message, f"✅ تم حذف الكروب: {group_link}")
                logger.info(f"تم حذف كروب: {group_link}")
            else:
                bot.reply_to(message, "❌ رقم غير صحيح")
        except:
            bot.reply_to(message, "❌ يرجى ارسال رقم صحيح")
        states.clear_state(user_id)
        return
    
    elif current_state == states.STATE_WAITING_DELETE_CLIP:
        # حذف كليشة
        clips = database.get_clips()
        try:
            clip_id = int(text)
            database.delete_clip(clip_id)
            bot.reply_to(message, f"✅ تم حذف الكليشة رقم {clip_id}")
            logger.info(f"تم حذف كليشة: {clip_id}")
        except:
            bot.reply_to(message, "❌ يرجى ارسال رقم صحيح")
        states.clear_state(user_id)
        return
    
    elif current_state == states.STATE_WAITING_TIMER:
        # تغيير المؤقت
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
        bot.reply_to(message, "✏️ ارسل الكليشات (كل سطر = كليشة واحدة)\nمثال:\nعاش العراق\nمحمد قوي")
    
    elif text == "👥 اضافة كروب":
        states.set_state(user_id, states.STATE_WAITING_GROUP)
        bot.reply_to(message, "🔗 ارسل رابط الكروب\nمثال: https://t.me/groupname")
    
    elif text == "❌ حذف حساب":
        accounts = database.get_accounts()
        if accounts:
            msg = "🗑️ *اختر الحساب للحذف (ارسل الرقم):*\n\n"
            for i, acc in enumerate(accounts, 1):
                msg += f"{i}. {acc[1]} (رسائل: {acc[4] or 0})\n"
            bot.reply_to(message, msg, parse_mode='Markdown')
            states.set_state(user_id, states.STATE_WAITING_DELETE_ACCOUNT)
        else:
            bot.reply_to(message, "❌ لا يوجد حسابات للحذف")
    
    elif text == "🚫 حذف كروب":
        groups = database.get_groups()
        if groups:
            msg = "🗑️ *اختر الكروب للحذف (ارسل الرقم):*\n\n"
            for i, grp in enumerate(groups, 1):
                msg += f"{i}. {grp[1]}\n"
            bot.reply_to(message, msg, parse_mode='Markdown')
            states.set_state(user_id, states.STATE_WAITING_DELETE_GROUP)
        else:
            bot.reply_to(message, "❌ لا يوجد كروبات للحذف")
    
    elif text == "🗑️ حذف كليشة":
        clips = database.get_clips()
        if clips:
            msg = "🗑️ *اختر الكليشة للحذف (ارسل الرقم):*\n\n"
            for clip in clips[:10]:  # عرض أول 10 كليشات فقط
                preview = clip[1][:30] + "..." if len(clip[1]) > 30 else clip[1]
                msg += f"{clip[0]}: {preview}\n"
            if len(clips) > 10:
                msg += f"\n... و {len(clips) - 10} كليشات أخرى"
            bot.reply_to(message, msg, parse_mode='Markdown')
            states.set_state(user_id, states.STATE_WAITING_DELETE_CLIP)
        else:
            bot.reply_to(message, "❌ لا يوجد كليشات للحذف")
    
    elif text == "⏹️ ايقاف البوت":
        scheduler.set_status(False)
        bot.reply_to(message, "⏸️ *تم ايقاف البوت*\nلن يتم ارسال أي رسائل", parse_mode='Markdown')
        logger.info("تم ايقاف البوت")
    
    elif text == "▶️ تشغيل البوت":
        scheduler.set_status(True)
        bot.reply_to(message, "▶️ *تم تشغيل البوت*\nسيتم ارسال الرسائل تلقائياً", parse_mode='Markdown')
        logger.info("تم تشغيل البوت")
    
    elif text == "⏱️ تغيير المؤقت":
        current_timer = scheduler.get_timer()
        states.set_state(user_id, states.STATE_WAITING_TIMER)
        bot.reply_to(message, f"⏰ *المؤقت الحالي:* {current_timer} ثانية\n\nارسل الوقت الجديد (بالثواني)\nمثال: 30", parse_mode='Markdown')
    
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
            f"📨 الحد اليومي: 50 رسالة/حساب"
        )
        bot.reply_to(message, stats, parse_mode='Markdown')
    
    else:
        bot.reply_to(message, "❌ زر غير معروف، استخدم الأزرار المتاحة")

# ========== تشغيل البوت ==========
if __name__ == "__main__":
    print("🤖 البوت يعمل...")
    bot.infinity_polling()
