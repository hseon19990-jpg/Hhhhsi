import os

# التوكن الخاص بالبوت (من متغيرات البيئة أو مباشرة)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "توكن_البوت_هنا")

# إعدادات المؤقت (بالثواني)
TIMER_DEFAULT = 60  # افتراضي دقيقة واحدة

# حالة البوت (تشغيل/ايقاف)
BOT_STATUS = True  # True = تشغيل, False = ايقاف

# مسار قاعدة البيانات
DB_PATH = "data/database.db"

# معرف المطور (اختياري)
ADMIN_ID = os.environ.get("ADMIN_ID", None)