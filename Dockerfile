FROM python:3.11-slim

WORKDIR /app

# کپی و نصب نیازمندی‌ها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی کدهای ربات
COPY . .

# دستور اجرا
CMD ["python", "bot.py"]
