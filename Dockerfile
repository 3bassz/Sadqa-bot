# استخدم Python 3.12 (مستقر وفيه مكتبة imghdr)
FROM python:3.12-slim

# تعيين مجلد العمل داخل الحاوية
WORKDIR /app

# نسخ requirements.txt وتثبيت المكتبات
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي ملفات المشروع
COPY . .

# أمر التشغيل الأساسي
CMD ["python", "main.py"]
