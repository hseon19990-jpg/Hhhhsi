import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
TIMER_DEFAULT = 60
DB_PATH = "data/database.db"
MAX_MESSAGES_PER_DAY = 50

# بيانات API لتليجرام (ثابتة)
API_ID = 6
API_HASH = "eb06d4abfb49dc3eeb1aeb98ae0f581e"

# التحقق من المطور (فقط محمد)
ADMIN_USERNAME = "Mohamed"  # يمكن تغييره
ADMIN_ID = os.environ.get("ADMIN_ID", None)  # معرف المستخدم
