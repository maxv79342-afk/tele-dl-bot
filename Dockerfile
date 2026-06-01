FROM python:3.11-slim

# نصب FFmpeg و پاکسازی کش برای کاهش حجم ایمیج
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# کپی و نصب وابستگی‌ها (لایه جداگانه برای استفاده از کش داکر)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# کپی سورس کد ربات
COPY . .

# اجرای ربات
CMD ["python", "bot.py"]
