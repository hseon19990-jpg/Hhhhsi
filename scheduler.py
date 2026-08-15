import time
import threading
from datetime import datetime
import database
from config import BOT_STATUS as CONFIG_STATUS

# متغيرات المؤقت
timer_seconds = int(database.get_setting("timer") or 60)
is_running = False
scheduler_thread = None
bot_instance = None  # سيتم تعيينه من bot.py

def set_bot_instance(bot):
    """تعيين كائن البوت للاستخدام في المؤقت"""
    global bot_instance
    bot_instance = bot

def start_scheduler():
    """بدء تشغيل المؤقت"""
    global is_running, scheduler_thread
    if not is_running:
        is_running = True
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        print(f"✅ تم تشغيل المؤقت ({timer_seconds} ثانية)")

def stop_scheduler():
    """ايقاف المؤقت"""
    global is_running
    is_running = False
    print("⏹️ تم ايقاف المؤقت")

def run_scheduler():
    """حلقة المؤقت الرئيسية"""
    global timer_seconds
    while is_running:
        try:
            # التحقق من حالة البوت من قاعدة البيانات
            status = database.get_setting("status")
            if status == "true":
                print(f"🔄 تنفيذ المهام في {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                execute_tasks()
            else:
                print("⏸️ البوت موقوف، انتظار...")
        except Exception as e:
            print(f"❌ خطأ في المؤقت: {e}")
        
        # الانتظار للفترة المحددة
        for _ in range(timer_seconds):
            if not is_running:
                break
            time.sleep(1)

def execute_tasks():
    """تنفيذ المهام المجدولة"""
    try:
        # الحصول على جميع الحسابات والكليشات والكروبات
        accounts = database.get_accounts()
        clips = database.get_clips()
        groups = database.get_groups()
        
        if not clips:
            print("⚠️ لا توجد كليشات لإرسالها")
            return
        
        # اختيار أول كليشة (يمكن تعديلها لارسال عشوائي)
        clip_text = clips[0][1]
        
        # ارسال الكليشة لكل حساب
        for account in accounts:
            username = account[1]
            send_to_account(username, clip_text)
        
        # ارسال الكليشة لكل كروب
        for group in groups:
            group_id = group[1]
            send_to_group(group_id, clip_text)
            
        print(f"✅ تم ارسال الكليشة إلى {len(accounts)} حساب و {len(groups)} كروب")
        
    except Exception as e:
        print(f"❌ خطأ في تنفيذ المهام: {e}")

def send_to_account(username, message):
    """ارسال رسالة إلى حساب (محاكاة)"""
    # في البوت الحقيقي، ستستخدم API التليجرام
    print(f"📨 ارسال إلى {username}: {message[:50]}...")

def send_to_group(group_id, message):
    """ارسال رسالة إلى كروب (محاكاة)"""
    # في البوت الحقيقي، ستستخدم API التليجرام
    print(f"👥 ارسال إلى {group_id}: {message[:50]}...")

def set_timer(seconds):
    """تغيير وقت المؤقت"""
    global timer_seconds
    try:
        seconds = int(seconds)
        if seconds < 5:
            return False, "⏱️ أقل وقت مسموح هو 5 ثواني"
        timer_seconds = seconds
        database.set_setting("timer", str(seconds))
        return True, f"⏱️ تم تغيير المؤقت إلى {seconds} ثانية"
    except ValueError:
        return False, "❌ يرجى ارسال رقم صحيح"

def get_timer():
    """الحصول على وقت المؤقت الحالي"""
    return timer_seconds

def get_status():
    """الحصول على حالة البوت"""
    status = database.get_setting("status")
    return status == "true"

def set_status(status):
    """تغيير حالة البوت"""
    database.set_setting("status", "true" if status else "false")