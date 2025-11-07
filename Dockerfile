# استفاده از پایتون 3.11
FROM python:3.11

# تنظیم پوشه کاری داخل کانتینر
WORKDIR /app

# کپی کردن فایل‌ها به داخل کانتینر
COPY . .

# نصب نیازمندی‌ها
RUN pip install --no-cache-dir -r requirements.txt

# اجرای ربات
CMD ["python", "bot.py"]