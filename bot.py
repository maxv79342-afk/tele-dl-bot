import os
import logging
import glob
import threading
import time
import requests
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
import yt_dlp
import uvicorn

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PORT = int(os.environ.get("PORT", 8000))
URL = os.getenv("RENDER_EXTERNAL_URL")
DOWNLOAD_DIR = "downloads"

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
application = Application.builder().token(TOKEN).build()

def keep_alive():
    while True:
        try:
            if URL:
                response = requests.get(f"https://{URL}/", timeout=10)
                logger.info(f"Keep-alive ping: {response.status_code}")
        except Exception as e:
            logger.error(f"Keep-alive failed: {e}")
        time.sleep(240)

keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
keep_alive_thread.start()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🚀 ربات دانلودر حرفه‌ای\n\n"
        "لینک ویدیو یا صوت را بفرست تا با کیفیت‌های مختلف دانلود کنم.\n\n"
        "🎵 خروجی صوتی MP3\n"
        "🎥 خروجی ویدیو با کیفیت‌های مختلف\n\n"
        "💡 نکته: حداکثر حجم فایل 50 مگابایت (محدودیت تلگرام)"
    )

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("❌ لطفاً یک لینک معتبر ارسال کنید.")
        return

    status_msg = await update.message.reply_text("🔍 در حال بررسی کیفیت‌های موجود...")
    ydl_opts = {'quiet': True, 'no_warnings': True}
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            video_qualities = {}
            audio_available = False
            for f_item in formats:
                if f_item.get('vcodec') != 'none' and f_item.get('height'):
                    video_qualities[f_item.get('height')] = True
                if f_item.get('acodec') != 'none':
                    audio_available = True
            
            keyboard = []
            if audio_available:
                keyboard.append([InlineKeyboardButton("🎵 فقط صوت (MP3 192k)", callback_data=f"audio|{url}")])
            for quality in sorted(video_qualities.keys(), reverse=True):
                if quality and quality <= 720:
                    keyboard.append([InlineKeyboardButton(f"🎥 ویدیو {quality}p", callback_data=f"video|{quality}|{url}")])
            
            if not keyboard:
                await status_msg.edit_text("❌ هیچ فرمتی برای دانلود پیدا نشد.")
                return
            await status_msg.edit_text("یک کیفیت انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Extract error: {e}")
        await status_msg.edit_text("❌ خطا در پردازش لینک")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("audio|"):
        action, url, quality = "audio", query.data[6:], None
    else:
        parts = query.data.split("|", 2)
        action, quality, url = "video", parts[1], parts[2]
    
    await query.edit_message_text("⏳ در حال دانلود... لطفاً کمی صبر کنید.")
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    outtmpl = f"{DOWNLOAD_DIR}/%(id)s.%(ext)s"
    
    if action == "audio":
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': outtmpl,
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
            'quiet': True,
        }
    else:
        ydl_opts = {
            'format': f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best',
            'outtmpl': outtmpl,
            'quiet': True,
            'merge_output_format': 'mp4',
        }
        
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if action == "audio":
                filename = os.path.splitext(filename)[0] + ".mp3"
                with open(filename, "rb") as audio_file:
                    await context.bot.send_audio(
                        chat_id=query.message.chat_id, audio=audio_file,
                        title=info.get('title', 'Audio'), caption=f"🎵 {info.get('title', 'Audio')}"
                    )
            else:
                base = os.path.splitext(filename)[0]
                final_file = filename
                for ext in ['mp4', 'mkv', 'webm']:
                    if os.path.exists(f"{base}.{ext}"):
                        final_file = f"{base}.{ext}"
                        break
                with open(final_file, "rb") as video_file:
                    await context.bot.send_document(
                        chat_id=query.message.chat_id, document=video_file,
                        filename=os.path.basename(final_file), caption=f"🎥 {info.get('title', 'Video')} - {quality}p"
                    )
        await query.edit_message_text("✅ دانلود با موفقیت انجام شد!")
        for f_item in glob.glob(f"{DOWNLOAD_DIR}/*"):
            try: os.remove(f_item)
            except: pass
    except Exception as e:
        logger.error(f"Download error: {e}")
        await query.edit_message_text("❌ خطا در دانلود")

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
application.add_handler(CallbackQueryHandler(button_handler))

@app.post("/" + TOKEN)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    await application.initialize()
    await application.start()
    if URL and TOKEN:
        # Render URL به صورت کامل با https:// می‌آید
        base_url = URL if URL.startswith("http") else f"https://{URL}"
        webhook_url = f"{base_url}/{TOKEN}"
        await application.bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook set to: {webhook_url}")

@app.on_event("shutdown")
async def on_shutdown():
    await application.stop()
    await application.shutdown()

@app.get("/")
def root():
    return {"status": "Bot is running!", "uptime": "24/7"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
