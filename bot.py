import telebot
from telebot import types
import logging
from config import BOT_TOKEN, ADMIN_ID
import database
import states
import scheduler

# إعداد التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# تهيئة البوت
bot = telebot.TeleBot(BOT_TOKEN)

# تعيين كائن البوت في المؤقت
scheduler.set_bot_instance(bot)

# تهيئة قاعدة البيانات
database.init_db()

# تشغيل المؤقت
scheduler.start_scheduler()

# ========== قائمة الأزرار ==========
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("➕ اضافة حساب")
    btn2 = types.KeyboardButton("📝 اضافة كليشة")
    btn3 = types.KeyboardButton("👥 اضافة كروب")
    btn4 = types.KeyboardButton("❌ حذف حساب")
    btn5 = types.KeyboardButton("🚫 حذف كروب")
    btn6 = types.KeyboardButton("🗑️ حذف كليشة")
    btn7 = types.KeyboardButton("⏹️ ايقاف البوت")
    btn8 = types.KeyboardButton("▶️ تشغيل البوت")
    btn9 = types.KeyboardButton("⏱️ تغيير المؤقت")
    btn10 = types.KeyboardButton("📊 الاحصائيات")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8, btn9, btn10)
    return markup

# ========== أمر /start ==========
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    welcome_msg = (
        "🤖 اهلاً بك في بوت سننشا!\n\n"
        "📌 هذا البوت مخصص لإدارة الحسابات والكليشات والكروبات\n"
        "📤 يقوم بإرسال الكليشات بشكل تلقائي وفق مؤقت زمني\n\n"
        "✨ اختر أحد الأزرار أدناه للبدء:"
    )
    bot.send_message(
        message.chat.id,
        welcome_msg,
        reply_markup=main_menu()
    )
    logger.info(f"مستخدم جديد: {user_id}")

# ========== أمر /help ==========
@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = (
        "🆘 *مساعدة البوت*\n\n"
        "➕ *اضافة حساب:* اضافة حساب تليجرام\n"
        "📝 *اضافة كليشة:* اضافة نص جديد\n"
        "👥 *اضافة كروب:* اضافة مجموعة\n"
        "❌ *حذف حساب:* حذف حساب موجود\n"
        "🚫 *حذف كروب:* حذف مجموعة\n"
        "🗑️ *حذف كليشة:* حذف نص\n"
        "⏹️ *ايقاف البوت:* ايقاف العمل\n"
        "▶️ *تشغيل البوت:* اعادة التشغيل\n"
        "⏱️ *تغيير المؤقت:* تغيير الفترة الزمنية\n"
        "📊 *الاحصائيات:* عرض احصائيات البوت"
    )
    bot.reply_to(message, help_text, parse_mode='Markdown')

# ========== معالجة الأزرار ==========
@bot.message_handler(func=lambda msg: True)
def handle_buttons(message):
    user_id = message.chat.id
    text = message.text
    
    # التحقق من الحالة أولاً
    current_state = states.get_state(user_id)
    
    if current_state == states.STATE_WAITING_ACCOUNT:
        # حفظ الحساب
        if text.startswith('@'):
            if database.add_account(text):
                bot.reply_to(message, f"✅ تم اضافة الحساب: {text}")
                logger.info(f"تم اضافة حساب: {text}")
            else:
                bot.reply_to(message, f"❌ الحساب {text} موجود مسبقاً")
        else:
            bot.reply_to(message, "❌ يرجى ارسال معرف صحيح يبدأ بـ @")
        states.clear_state(user_id)
        return
        
    elif current_state == states.STATE_WAITING_CLIP:
        # حفظ الكليشة
        if len(text) > 10:
            database.add_clip(text)
            bot.reply_to(message, "✅ تم اضافة الكليشة بنجاح")
            logger.info(f"تم اضافة كليشة جديدة")
        else:
            bot.reply_to(message, "❌ الكليشة قصيرة جداً (يجب أن تكون أكثر من 10 حروف)")
        states.clear_state(user_id)
        return
        
    elif current_state == states.STATE_WAITING_GROUP:
        # حفظ الكروب
        if text.startswith('@') or text.startswith('-'):
            if database.add_group(text):
                bot.reply_to(message, f"✅ تم اضافة الكروب: {text}")
                logger.info(f"تم اضافة كروب: {text}")
            else:
                bot.reply_to(message, f"❌ الكروب {text} موجود مسبقاً")
        else:
            bot.reply_to(message, "❌ يرجى ارسال معرف كروب صحيح")
        states.clear_state(user_id)
        return
        
    elif current_state == states.STATE_WAITING_DELETE_ACCOUNT:
        # حذف حساب
        try:
            account_id = int(text)
            account = database.get_accounts()
            if account_id <= len(account):
                username = account[account_id-1][1]
                database.delete_account(username)
                bot.reply_to(message, f"✅ تم حذف الحساب: {username}")
                logger.info(f"تم حذف حساب: {username}")
            else:
                bot.reply_to(message, "❌ رقم غير صحيح")
        except:
            bot.reply_to(message, "❌ يرجى ارسال رقم صحيح")
        states.clear_state(user_id)
        return
        
    elif current_state == states.STATE_WAITING_DELETE_GROUP:
        # حذف كروب
        try:
            group_id = int(text)
            groups = database.get_groups()
            if group_id <= len(groups):
                group = groups[group_id-1][1]
                database.delete_group(group)
                bot.reply_to(message, f"✅ تم حذف الكروب: {group}")
                logger.info(f"تم حذف كروب: {group}")
            else:
                bot.reply_to(message, "❌ رقم غير صحيح")
        except:
            bot.reply_to(message, "❌ يرجى ارسال رقم صحيح")
        states.clear_state(user_id)
        return
        
    elif current_state == states.STATE_WAITING_DELETE_CLIP:
        # حذف كليشة
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
        if success:
            bot.reply_to(message, msg)
            logger.info(f"تم تغيير المؤقت إلى: {text}")
        else:
            bot.reply_to(message, msg)
        states.clear_state(user_id)
        return
    
    # معالجة الأزرار الرئيسية
    if text == "➕ اضافة حساب":
        states.set_state(user_id, states.STATE_WAITING_ACCOUNT)
        bot.reply_to(message, "📨 ارسل معرف الحساب (مثال: @username)")
        
    elif text == "📝 اضافة كليشة":
        states.set_state(user_id, states.STATE_WAITING_CLIP)
        bot.reply_to(message, "✏️ ارسل الكليشة الجديدة (أكثر من 10 حروف)")
        
    elif text == "👥 اضافة كروب":
        states.set_state(user_id, states.STATE_WAITING_GROUP)
        bot.reply_to(message, "🔗 ارسل معرف الكروب (مثال: @groupname)")
        
    elif text == "❌ حذف حساب":
        accounts = database.get_accounts()
        if accounts:
            msg = "🗑️ *اختر الحساب للحذف (ارسل الرقم):*\n\n"
            for i, acc in enumerate(accounts, 1):
                msg += f"{i}. {acc[1]} (اضيف: {acc[2]})\n"
            bot.reply_to(message, msg, parse_mode='Markdown')
            states.set_state(user_id, states.STATE_WAITING_DELETE_ACCOUNT)
        else:
            bot.reply_to(message, "❌ لا يوجد حسابات للحذف")
            
    elif text == "🚫 حذف كروب":
        groups = database.get_groups()
        if groups:
            msg = "🗑️ *اختر الكروب للحذف (ارسل الرقم):*\n\n"
            for i, grp in enumerate(groups, 1):
                msg += f"{i}. {grp[1]} (اضيف: {grp[2]})\n"
            bot.reply_to(message, msg, parse_mode='Markdown')
            states.set_state(user_id, states.STATE_WAITING_DELETE_GROUP)
        else:
            bot.reply_to(message, "❌ لا يوجد كروبات للحذف")
            
    elif text == "🗑️ حذف كليشة":
        clips = database.get_clips()
        if clips:
            msg = "🗑️ *اختر الكليشة للحذف (ارسل الرقم):*\n\n"
            for clip in clips:
                preview = clip[1][:50] + "..." if len(clip[1]) > 50 else clip[1]
                msg += f"{clip[0]}: {preview}\n"
            bot.reply_to(message, msg, parse_mode='Markdown')
            states.set_state(user_id, states.STATE_WAITING_DELETE_CLIP)
        else:
            bot.reply_to(message, "❌ لا يوجد كليشات للحذف")
            
    elif text == "⏹️ ايقاف البوت":
        scheduler.set_status(False)
        bot.reply_to(message, "⏸️ *تم ايقاف البوت*\nلن يتم ارسال أي كليشات", parse_mode='Markdown')
        logger.info("تم ايقاف البوت")
        
    elif text == "▶️ تشغيل البوت":
        scheduler.set_status(True)
        bot.reply_to(message, "▶️ *تم تشغيل البوت*\nسيتم ارسال الكليشات تلقائياً", parse_mode='Markdown')
        logger.info("تم تشغيل البوت")
        
    elif text == "⏱️ تغيير المؤقت":
        current_timer = scheduler.get_timer()
        states.set_state(user_id, states.STATE_WAITING_TIMER)
        bot.reply_to(message, f"⏰ *المؤقت الحالي:* {current_timer} ثانية\n\nارسل الوقت الجديد (بالثواني)\nمثال: 30", parse_mode='Markdown')
        
    elif text == "📊 الاحصائيات":
        accounts = database.get_accounts()
        clips = database.get_clips()
        groups = database.get_groups()
        status = "🟢 يعمل" if scheduler.get_status() else "🔴 موقوف"
        timer = scheduler.get_timer()
        
        stats = (
            f"📊 *احصائيات البوت*\n\n"
            f"👤 الحسابات: {len(accounts)}\n"
            f"📝 الكليشات: {len(clips)}\n"
            f"👥 الكروبات: {len(groups)}\n"
            f"⏱️ المؤقت: {timer} ثانية\n"
            f"📌 الحالة: {status}\n"
            f"🔄 اخر تشغيل: {scheduler.last_run if hasattr(scheduler, 'last_run') else 'غير معروف'}"
        )
        bot.reply_to(message, stats, parse_mode='Markdown')
    
    else:
        bot.reply_to(message, "❌ زر غير معروف، استخدم الأزرار المتاحة")

# ========== معالجة الأخطاء ==========
@bot.message_handler(content_types=['text'])
def handle_unknown(message):
    if states.get_state(message.chat.id) == states.STATE_NONE:
        bot.reply_to(message, "❌ استخدم الأزرار للتحكم بالبوت")

# ========== تشغيل البوت ==========
if __name__ == "__main__":
    try:
        logger.info("🤖 بدء تشغيل البوت...")
        print("🤖 البوت يعمل الآن...")
        print(f"⏱️ المؤقت: {scheduler.get_timer()} ثانية")
        print(f"📊 الحالة: {'يعمل' if scheduler.get_status() else 'موقوف'}")
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        logger.error(f"خطأ في تشغيل البوت: {e}")
        print(f"❌ خطأ: {e}")