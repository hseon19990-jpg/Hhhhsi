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
    
    # ... (معالجة الحالات مثل السابق)
    
    # الأزرار الرئيسية
    if text == "➕ اضافة حساب":
        states.set_state(user_id, states.STATE_WAITING_ACCOUNT)
        bot.reply_to(message, "📱 ارسل رقم الهاتف مع مفتاح الدولة\nمثال: 9647812345678")
    
    elif text == "📝 اضافة كليشة":
        states.set_state(user_id, states.STATE_WAITING_CLIP)
        bot.reply_to(message, "✏️ ارسل الكليشة (كل سطر = كليشة واحدة)")
    
    elif text == "👥 اضافة كروب":
        states.set_state(user_id, states.STATE_WAITING_GROUP)
        bot.reply_to(message, "🔗 ارسل رابط الكروب\nمثال: https://t.me/groupname")
    
    # ... (باقي الأزرار)
    
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

# ========== تشغيل البوت ==========
if __name__ == "__main__":
    print("🤖 البوت يعمل...")
    bot.infinity_polling()