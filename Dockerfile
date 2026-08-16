FROM python:3.10-slim

# تعيين مجلد العمل
WORKDIR /app

# تثبيت الاعتماديات الأساسية
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# نسخ ملف المتطلبات أولاً (للاستفادة من cache)
COPY requirements.txt .

# تثبيت المكتبات
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي الملفات
COPY . .

# تشغيل البوت
ENV PYTHONUNBUFFERED=1
CMD ["python", "-u", "bot.py"]
