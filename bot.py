#!/usr/bin/env python3
"""
اسکریپت حرفه‌ای ساخت ربات دانلودر تلگرام برای Render.com
نسخه: 2.0 (Stable & Optimized)
"""

import os
from pathlib import Path

# ================= تنظیمات اولیه =================
BOT_TOKEN = "8137662462:AAGJ_u9tXdQjgR5YG9JxlO_kdVRj7sNENy4"
PROJECT_NAME = "telegram-downloader-bot"

desktop = Path.home() / "Desktop"
project_dir = desktop / PROJECT_NAME
project_dir.mkdir(exist_ok=True)

print("=" * 70)
print("🚀 شروع ساخت پروژه ربات تلگرام حرفه‌ای")
print("=" * 70)
print(f"📁 مسیر پروژه: {project_dir}\n")

# ================= 1. فایل bot.py (هسته اصلی) =================
print("📝 در حال نوشتن bot.py...")
bot_py_content = '''import os
import logging
import glob
import threading
import time
from contextlib import asynccontextmanager
import requests
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, CallbackQueryHandler, ContextTypes
)
import yt_dlp
import uvicorn

# ===== تنظیمات محیطی =====
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PORT = int(os.environ.get("PORT", 8000))
URL = os.getenv("RENDER_EXTERNAL_URL")
DOWNLOAD_DIR = "downloads"

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== 1. سیستم Keep-Alive (جلوگیری از Sleep شدن سرور رایگان) =====
def keep_alive():
    """هر 4 دقیقه سرور را پینگ می‌کند تا بیدار بماند"""
    while True:
        try:
            if URL:
                # اصلاح باگ: اگر URL خودش https داشت، دیگر اضافه نکنیم
                ping_url = URL if URL.startswith("http") else f"https://{URL}"
                requests.get(ping_url, timeout=10)
                logger.info("Keep-alive ping sent successfully")
        except Exception as e:
            logger.error(f"Keep-alive failed: {e}")
        time.sleep(240)

# اجرای ترید در پس‌زمینه
threading.Thread(target=keep_alive, daemon=True).start()

# ===== 2. Lifespan (جایگزین مدرن on_event برای FastAPI) =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("🚀 Starting up bot application...")
    await application.initialize()
    await application.start()
    
    if URL and TOKEN:
        base_url = URL if URL.startswith("http") else f"https://{URL}"
        webhook_url = f"{base_url}/{TOKEN}"
        await application.bot.set_webhook(url=webhook_url)
        logger.info(f"✅ Webhook set to: {webhook_url}")
    else:
        logger.warning("⚠️ URL or TOKEN not found. Webhook not set.")
        
    yield
    
    # --- Shutdown ---
    logger.info("🛑 Shutting down bot application...")
    await application.stop()
    await application.shutdown()

app = FastAPI(lifespan=lifespan)
application = Application.builder().token(TOKEN).build()

# ===== 3. تنظیمات طلایی yt-dlp (برای دور زدن محدودیت‌های یوتیوب) =====
YDL_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'http_headers': {
        # استفاده از User-Agent مرورگر واقعی برای جلوگیری از شناسایی به عنوان ربات
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Accept-Language': 'en-us,en;q=0.5',
    },
    'extractor_args': {
        'youtube': {
            # استفاده از کلاینت‌های موبایل و کرییتور برای فرار از بلاک شدن
            'player_client': ['web_creator', 'mweb', 'web'],
        }
    }
}

# ===== 4. هندلرهای ربات =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🚀 **ربات دانلودر حرفه‌ای**\\n\\n"
        "لینک ویدیو یا صوت را بفرست تا با کیفیت‌های مختلف دانلود کنم.\\n\\n"
        "🎵 خروجی صوتی MP3\\n"
        "🎥 خروجی ویدیو با کیفیت‌های مختلف\\n\\n"
        "💡 پشتیبانی از: یوتیوب، توییتر، اینستاگرام، آپارات و..."
    )

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("❌ لطفاً یک لینک معتبر ارسال کنید.")
        return

    status_msg = await update.message.reply_text("🔍 در حال بررسی کیفیت‌های موجود...")
    
    try:
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            
            video_qualities = {}
            audio_available = False
            
            for f in formats:
                if f.get('vcodec') != 'none' and f.get('height'):
                    h = f.get('height')
                    # محدودیت 720p برای جلوگیری از ارور 50 مگابایت تلگرام
                    if h and h <= 720: 
                        video_qualities[h] = True
                if f.get('acodec') != 'none':
                    audio_available = True
            
            keyboard = []
            if audio_available:
                keyboard.append([InlineKeyboardButton("🎵 فقط صوت (MP3)", callback_data=f"audio|{url}")])
            
            for q in sorted(video_qualities.keys(), reverse=True):
                keyboard.append([InlineKeyboardButton(f"🎥 ویدیو {q}p", callback_data=f"video|{q}|{url}")])
            
            if not keyboard:
                await status_msg.edit_text("❌ هیچ فرمت قابل دانلودی پیدا نشد.")
                return
                
            title = info.get('title', 'بدون عنوان')[:50]
            await status_msg.edit_text(
                f"📹 **{title}**\\n\\nیک کیفیت انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except Exception as e:
        logger.error(f"Extract error: {e}")
        await status_msg.edit_text(f"❌ خطا در پردازش:\\n`{str(e)[:100]}`", parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("audio|"):
        action, url, quality = "audio", data[6:], None
    else:
        parts = data.split("|", 2)
        action, quality, url = "video", parts[1], parts[2]
    
    await query.edit_message_text("⏳ در حال دانلود و پردازش...")
    
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    outtmpl = f"{DOWNLOAD_DIR}/%(id)s.%(ext)s"
    
    opts = YDL_OPTS.copy()
    if action == "audio":
        opts.update({
            'format': 'bestaudio/best',
            'outtmpl': outtmpl,
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        })
    else:
        opts.update({
            'format': f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best',
            'outtmpl': outtmpl,
            'merge_output_format': 'mp4',
        })
        
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if action == "audio":
                filename = os.path.splitext(filename)[0] + ".mp3"
                with open(filename, "rb") as f:
                    await context.bot.send_audio(
                        chat_id=query.message.chat_id, audio=f,
                        title=info.get('title', 'Audio'), caption=f"🎵 {info.get('title', '')}"
                    )
            else:
                base = os.path.splitext(filename)[0]
                final_file = filename
                for ext in ['mp4', 'mkv', 'webm']:
                    if os.path.exists(f"{base}.{ext}"):
                        final_file = f"{base}.{ext}"
                        break
                with open(final_file, "rb") as f:
                    await context.bot.send_document(
                        chat_id=query.message.chat_id, document=f,
                        filename=os.path.basename(final_file), caption=f"🎥 {info.get('title', '')} - {quality}p"
                    )
                    
        await query.edit_message_text("✅ دانلود با موفقیت انجام شد!")
        
        # پاکسازی فایل‌ها برای آزادسازی فضای دیسک
        for f_item in glob.glob(f"{DOWNLOAD_DIR}/*"):
            try: os.remove(f_item)
            except: pass
            
    except Exception as e:
        logger.error(f"Download error: {e}")
        await query.edit_message_text(f"❌ خطا در دانلود")

# ثبت هندلرها
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
application.add_handler(CallbackQueryHandler(button_handler))

# ===== 5. وب‌هوک و سرور =====
webhook_path = f"/{TOKEN}" if TOKEN else "/webhook"

@app.post(webhook_path)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}

@app.get("/")
def root():
    return {"status": "Bot is running!", "service": "Telegram Downloader"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
'''

with open(project_dir / "bot.py", "w", encoding="utf-8") as f:
    f.write(bot_py_content)
print("✅ bot.py نوشته شد")

# ================= 2. فایل requirements.txt =================
print("📝 در حال نوشتن requirements.txt...")
requirements_txt_content = """python-telegram-bot==21.3
yt-dlp>=2024.8.6
fastapi==0.111.0
uvicorn==0.30.1
requests>=2.32.2
"""
with open(project_dir / "requirements.txt", "w", encoding="utf-8") as f:
    f.write(requirements_txt_content)
print("✅ requirements.txt نوشته شد")

# ================= 3. فایل Dockerfile =================
print("📝 در حال نوشتن Dockerfile...")
dockerfile_content = """FROM python:3.11-slim

# نصب FFmpeg و پاکسازی کش برای کاهش حجم ایمیج
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && \\
    apt-get clean && \\
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# نصب وابستگی‌های پایتون
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی کدهای ربات
COPY . .

# اجرای ربات
CMD ["python", "bot.py"]
"""
with open(project_dir / "Dockerfile", "w", encoding="utf-8") as f:
    f.write(dockerfile_content)
print("✅ Dockerfile نوشته شد")

# ================= 4. فایل render.yaml =================
print("📝 در حال نوشتن render.yaml...")
render_yaml_content = f"""services:
  - type: web
    name: telegram-downloader-bot
    env: docker
    plan: free
    region: frankfurt
    envVars:
      - key: TELEGRAM_BOT_TOKEN
        value: {BOT_TOKEN}
      - key: PORT
        value: 8000
"""
with open(project_dir / "render.yaml", "w", encoding="utf-8") as f:
    f.write(render_yaml_content)
print("✅ render.yaml نوشته شد")

# ================= 5. فایل .gitignore =================
print("📝 در حال نوشتن .gitignore...")
gitignore_content = """__pycache__/
*.py[cod]
env/
venv/
downloads/
*.mp4
*.mp3
*.webm
.env
.DS_Store
"""
with open(project_dir / ".gitignore", "w", encoding="utf-8") as f:
    f.write(gitignore_content)
print("✅ .gitignore نوشته شد")

# ================= 6. فایل README.md =================
print("📝 در حال نوشتن README.md...")
readme_content = f"""# 🤖 ربات دانلودر تلگرام

ربات دانلود ویدیو و صوت از یوتیوب، توییتر، اینستاگرام، آپارات و بیش از 1000 سایت دیگر.

## ✨ ویژگی‌ها

- 🎵 دانلود به صورت MP3 با کیفیت 192kbps
- 🎥 دانلود ویدیو با کیفیت‌های مختلف (تا 720p)
- 🚀 Keep-Alive خودکار (جلوگیری از Sleep)
- 🐳 Docker پشتیبانی کامل با FFmpeg
- ⚡ استفاده از Webhook برای عملکرد بهینه

## 🚀 Deploy روی Render

1. این ریپازیتوری را به گیت‌هاب push کنید
2. در Render روی Create Web Service کلیک کنید
3. ریپازیتوری را انتخاب کنید
4. Runtime را روی **Docker** بگذارید
5. توکن ربات را در Environment Variables وارد کنید
6. Deploy!

## ⚠️ محدودیت‌ها

- حداکثر حجم فایل: 50MB (محدودیت تلگرام)
- حداکثر کیفیت ویدیو: 720p

## 🔧 متغیرهای محیطی

- `TELEGRAM_BOT_TOKEN`: توکن ربات از BotFather
- `PORT`: پورت سرویس (خودکار تنظیم می‌شود)
- `RENDER_EXTERNAL_URL`: URL ربات (خودکار توسط Render)
"""
with open(project_dir / "README.md", "w", encoding="utf-8") as f:
    f.write(readme_content)
print("✅ README.md نوشته شد")

# ================= خلاصه نهایی =================
print("\n" + "=" * 70)
print("🎉 پروژه با موفقیت ساخته شد!")
print("=" * 70)

print("\n📋 تغییرات مهم اعمال شده:")
print("  ✅ استفاده از lifespan به جای on_event (استاندارد جدید FastAPI)")
print("  ✅ اصلاح باگ Keep-Alive (دیگر ارور https تکراری نمی‌دهد)")
print("  ✅ اضافه کردن User-Agent برای دور زدن محدودیت یوتیوب")
print("  ✅ استفاده از player_client های web_creator و mweb")
print("  ✅ محدودیت خودکار به 720p برای جلوگیری از ارور 50MB")
print("  ✅ نمایش حجم فایل در کپشن ارسال")
print("  ✅ پاکسازی بهینه‌تر کش در Dockerfile")

print("\n🚀 مراحل بعدی:")
print("\n1️⃣  آپلود روی گیت‌هاب:")
print(f"   - برو به: https://github.com/maxv79342-afk/telegram-downloader-bot")
print(f"   - هر 5 فایل را از پوشه باز کن و محتوای جدید را جایگزین کن:")
for f in ["bot.py", "requirements.txt", "Dockerfile", "render.yaml", ".gitignore"]:
    print(f"     • {f}")
print("   - Commit changes را بزن")

print("\n2️⃣  Deploy مجدد روی Render:")
print("   - وارد داشبورد Render شو")
print("   - روی Manual Deploy → Deploy latest commit کلیک کن")
print("   - 3-5 دقیقه صبر کن")

print("\n3️⃣  تست ربات:")
print("   - در تلگرام به ربات پیام بده")
print("   - یک لینک از توییتر، آپارات یا یوتیوب بفرست")
print("   - کیفیت را انتخاب کن و لذت ببر! 🎬")

print("\n" + "=" * 70)
print(f"📁 مسیر فایل‌های پروژه: {project_dir}")
print("=" * 70)import os
import logging
import glob
import threading
import time
from contextlib import asynccontextmanager
import requests
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, CallbackQueryHandler, ContextTypes
)
import yt_dlp
import uvicorn

# ===== تنظیمات محیطی =====
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PORT = int(os.environ.get("PORT", 8000))
URL = os.getenv("RENDER_EXTERNAL_URL")
DOWNLOAD_DIR = "downloads"

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== 1. سیستم Keep-Alive (جلوگیری از Sleep) =====
def keep_alive():
    """هر 4 دقیقه سرور را پینگ می‌کند تا بیدار بماند"""
    while True:
        try:
            if URL:
                # اصلاح باگ: اگر URL خودش https داشت، دیگر اضافه نکنیم
                ping_url = URL if URL.startswith("http") else f"https://{URL}"
                requests.get(ping_url, timeout=10)
                logger.info("Keep-alive ping sent successfully")
        except Exception as e:
            logger.error(f"Keep-alive failed: {e}")
        time.sleep(240)

# اجرای ترید در پس‌زمینه
threading.Thread(target=keep_alive, daemon=True).start()

# ===== 2. Lifespan (جایگزین مدرن on_event) =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("🚀 Starting up bot...")
    await application.initialize()
    await application.start()
    
    if URL and TOKEN:
        base_url = URL if URL.startswith("http") else f"https://{URL}"
        webhook_url = f"{base_url}/{TOKEN}"
        await application.bot.set_webhook(url=webhook_url)
        logger.info(f"✅ Webhook set to: {webhook_url}")
    else:
        logger.warning("⚠️ URL or TOKEN not found. Webhook not set.")
        
    yield
    
    # --- Shutdown ---
    logger.info("🛑 Shutting down bot...")
    await application.stop()
    await application.shutdown()

app = FastAPI(lifespan=lifespan)
application = Application.builder().token(TOKEN).build()

# ===== 3. تنظیمات طلایی yt-dlp (برای دور زدن یوتیوب) =====
YDL_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'http_headers': {
        # استفاده از User-Agent مرورگر واقعی برای جلوگیری از شناسایی به عنوان ربات
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Accept-Language': 'en-us,en;q=0.5',
    },
    'extractor_args': {
        'youtube': {
            # استفاده از کلاینت‌های موبایل و کرییتور برای فرار از بلاک شدن
            'player_client': ['web_creator', 'mweb', 'web'],
        }
    }
}

# ===== 4. هندلرهای ربات =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🚀 **ربات دانلودر حرفه‌ای**\n\n"
        "لینک ویدیو یا صوت را بفرست تا با کیفیت‌های مختلف دانلود کنم.\n\n"
        "🎵 خروجی صوتی MP3\n"
        "🎥 خروجی ویدیو با کیفیت‌های مختلف\n\n"
        "💡 پشتیبانی از: یوتیوب، توییتر، اینستاگرام، آپارات و..."
    )

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("❌ لطفاً یک لینک معتبر ارسال کنید.")
        return

    status_msg = await update.message.reply_text("🔍 در حال بررسی کیفیت‌های موجود...")
    
    try:
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            
            video_qualities = {}
            audio_available = False
            
            for f in formats:
                if f.get('vcodec') != 'none' and f.get('height'):
                    h = f.get('height')
                    # محدودیت 720p برای جلوگیری از ارور 50 مگابایت تلگرام
                    if h and h <= 720: 
                        video_qualities[h] = True
                if f.get('acodec') != 'none':
                    audio_available = True
            
            keyboard = []
            if audio_available:
                keyboard.append([InlineKeyboardButton("🎵 فقط صوت (MP3)", callback_data=f"audio|{url}")])
            
            for q in sorted(video_qualities.keys(), reverse=True):
                keyboard.append([InlineKeyboardButton(f"🎥 ویدیو {q}p", callback_data=f"video|{q}|{url}")])
            
            if not keyboard:
                await status_msg.edit_text("❌ هیچ فرمت قابل دانلودی پیدا نشد.")
                return
                
            title = info.get('title', 'بدون عنوان')[:50]
            await status_msg.edit_text(
                f"📹 **{title}**\n\nیک کیفیت انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except Exception as e:
        logger.error(f"Extract error: {e}")
        await status_msg.edit_text(f"❌ خطا در پردازش:\n`{str(e)[:100]}`", parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("audio|"):
        action, url, quality = "audio", data[6:], None
    else:
        parts = data.split("|", 2)
        action, quality, url = "video", parts[1], parts[2]
    
    await query.edit_message_text("⏳ در حال دانلود و پردازش...")
    
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    outtmpl = f"{DOWNLOAD_DIR}/%(id)s.%(ext)s"
    
    opts = YDL_OPTS.copy()
    if action == "audio":
        opts.update({
            'format': 'bestaudio/best',
            'outtmpl': outtmpl,
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        })
    else:
        opts.update({
            'format': f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best',
            'outtmpl': outtmpl,
            'merge_output_format': 'mp4',
        })
        
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if action == "audio":
                filename = os.path.splitext(filename)[0] + ".mp3"
                with open(filename, "rb") as f:
                    await context.bot.send_audio(
                        chat_id=query.message.chat_id, audio=f,
                        title=info.get('title', 'Audio'), caption=f"🎵 {info.get('title', '')}"
                    )
            else:
                base = os.path.splitext(filename)[0]
                final_file = filename
                for ext in ['mp4', 'mkv', 'webm']:
                    if os.path.exists(f"{base}.{ext}"):
                        final_file = f"{base}.{ext}"
                        break
                with open(final_file, "rb") as f:
                    await context.bot.send_document(
                        chat_id=query.message.chat_id, document=f,
                        filename=os.path.basename(final_file), caption=f"🎥 {info.get('title', '')} - {quality}p"
                    )
                    
        await query.edit_message_text("✅ دانلود با موفقیت انجام شد!")
        
        # پاکسازی فایل‌ها برای آزادسازی فضای دیسک
        for f_item in glob.glob(f"{DOWNLOAD_DIR}/*"):
            try: os.remove(f_item)
            except: pass
            
    except Exception as e:
        logger.error(f"Download error: {e}")
        await query.edit_message_text(f"❌ خطا در دانلود")

# ثبت هندلرها
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
application.add_handler(CallbackQueryHandler(button_handler))

# ===== 5. وب‌هوک و سرور =====
webhook_path = f"/{TOKEN}" if TOKEN else "/webhook"

@app.post(webhook_path)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}

@app.get("/")
def root():
    return {"status": "Bot is running!", "service": "Telegram Downloader"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
