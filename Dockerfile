# استفاده از پایتون سبک
FROM python:3.10-slim

# نصب وابستگی‌های سیستمی لازم برای tgcrypto
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev && rm -rf /var/lib/apt/lists/*

# تنظیم پوشه کاری
WORKDIR /app

# کپی و نصب نیازمندی‌های پایتون
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی کدهای ربات
COPY . .

# اجرای ربات
CMD ["python", "bot.py"]
