import time
import threading
import random
from datetime import datetime, timedelta
import database
from config import MAX_MESSAGES_PER_DAY

timer_seconds = 60
is_running = False
accounts = []
groups = []
clips = []
current_account_index = 0
last_run = None

def start_scheduler():
    global is_running, timer_seconds, accounts, groups, clips
    if not is_running:
        # تحميل البيانات
        timer_value = database.get_setting("timer")
        timer_seconds = int(timer_value) if timer_value else 60
        accounts = database.get_accounts()
        groups = database.get_groups()
        clips = database.get_clips()
        
        is_running = True
        thread = threading.Thread(target=run_scheduler, daemon=True)
        thread.start()
        print(f"✅ تم تشغيل المؤقت ({timer_seconds} ثانية)")
        print(f"📊 حسابات: {len(accounts)}, كروبات: {len(groups)}, كليشات: {len(clips)}")

def stop_scheduler():
    global is_running
    is_running = False
    print("⏹️ تم ايقاف المؤقت")

def run_scheduler():
    global timer_seconds, accounts, groups, clips, current_account_index, last_run
    
    # إعادة تعيين العدادات اليومية
    database.reset_daily_messages()
    
    while is_running:
        try:
            status = database.get_setting("status")
            if status == "true":
                # تحديث البيانات
                accounts = database.get_accounts()
                groups = database.get_groups()
                clips = database.get_clips()
                
                if accounts and groups and clips:
                    execute_next_message()
                    last_run = datetime.now()
                else:
                    print("⚠️ بيانات ناقصة: حسابات/كروبات/كليشات")
            else:
                print("⏸️ البوت موقوف")
                
        except Exception as e:
            print(f"❌ خطأ: {e}")
        
        # انتظار المؤقت
        for _ in range(timer_seconds):
            if not is_running:
                break
            time.sleep(1)

def execute_next_message():
    global current_account_index, accounts, groups, clips
    
    if not accounts or not groups or not clips:
        return
    
    # اختيار حساب بالتناوب
    account = accounts[current_account_index % len(accounts)]
    current_account_index += 1
    
    account_id = account[0]
    phone = account[1]
    messages_sent = account[4] or 0
    
    # التحقق من الحد اليومي
    if messages_sent >= MAX_MESSAGES_PER_DAY:
        print(f"⚠️ الحساب {phone} وصل للحد اليومي ({MAX_MESSAGES_PER_DAY})")
        return
    
    # اختيار كروب عشوائي
    available_groups = []
    for group in groups:
        group_id = group[0]
        group_link = group[1]
        # تجنب الكروبات التي أرسل لها هذا الحساب اليوم
        if not database.has_sent_today(account_id, group_id):
            available_groups.append(group)
    
    if not available_groups:
        print(f"⚠️ لا توجد كروبات متاحة للحساب {phone}")
        return
    
    group = random.choice(available_groups)
    group_id = group[0]
    group_link = group[1]
    
    # اختيار كليشة عشوائية
    clip = random.choice(clips)
    clip_id = clip[0]
    clip_text = clip[1]
    
    # محاكاة الإرسال (هنا ستضيف كود الإرسال الحقيقي)
    print(f"📨 [{phone}] → {group_link} : {clip_text[:50]}...")
    
    # تسجيل الإرسال
    database.increment_messages(phone)
    database.log_sent(account_id, group_id, clip_id)
    
    print(f"✅ تم الإرسال بواسطة {phone} (رسالة {messages_sent + 1}/{MAX_MESSAGES_PER_DAY})")

def set_timer(seconds):
    global timer_seconds
    try:
        seconds = int(seconds)
        if seconds < 5:
            return False, "⏱️ أقل وقت 5 ثواني"
        timer_seconds = seconds
        database.set_setting("timer", str(seconds))
        return True, f"⏱️ تم تغيير المؤقت إلى {seconds} ثانية"
    except ValueError:
        return False, "❌ يرجى ارسال رقم صحيح"

def get_timer():
    return timer_seconds

def get_status():
    try:
        return database.get_setting("status") == "true"
    except:
        return True

def set_status(status):
    database.set_setting("status", "true" if status else "false")