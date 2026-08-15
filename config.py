import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "توكن_البوت_هنا")
TIMER_DEFAULT = 60  # المؤقت بين كل حساب وآخر
DB_PATH = "data/database.db"

# إعدادات النشر
MAX_MESSAGES_PER_DAY = 50  # عدد الرسائل لكل حساب يومياً