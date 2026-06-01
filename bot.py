#!/usr/bin/env python3
import os
import logging
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# تنظیمات لاگ‌گیری برای دیباگ در Render
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ⚠️ توکن ربات به صورت مستقیم تنظیم شد (مراقب لو رفتن آن در گیت‌هاب باشید!)
TOKEN = "8137662462:AAGJ_u9tXdQjgR5YG9JxlO_kdVRj7sNENy4"

# این دو متغیر را نباید هاردکد کنید، Render خودش این ها را به کد شما می‌دهد
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.getenv("PORT", "10000"))

# پوشه دانلود
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 سلام! من ربات پردازش فایل هستم.\n\n"
        "⚠️ توجه: به دلیل محدودیت‌های سرورهای تلگرام، فقط فایل‌های **زیر ۲۰ مگابایت** قابل پردازش هستند."
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت فایل، ذخیره روی هارد (بدون مصرف رم)، و آپلود مجدد"""
    message = update.message
    doc = message.document or message.video or message.audio
    
    if not doc:
        await message.reply_text("لطفاً یک فایل، ویدیو یا صدا ارسال کنید.")
        return

    file_size_mb = doc.file_size / (1024 * 1024)
    
    # محدودیت دانلود API رسمی تلگرام (20MB)
    if file_size_mb > 20:
        await message.reply_text(f"❌ حجم فایل شما {file_size_mb:.1f} مگابایت است.\nدانلود فایل‌های بالای ۲۰ مگابایت در API رسمی تلگرام ممکن نیست.")
        return

    status_msg = await message.reply_text("⏳ در حال دریافت فایل...")

    try:
        # دریافت آبجکت فایل
        telegram_file = await context.bot.get_file(doc.file_id)
        
        # نام و مسیر فایل
        file_name = getattr(doc, 'file_name', None) or f"{doc.file_unique_id}.dat"
        local_path = DOWNLOAD_DIR / file_name

        # دانلود مستقیم روی هارد سرور (استریم کردن - فشار صفر به رم)
        await telegram_file.download_to_drive(custom_path=str(local_path))

        await status_msg.edit_text("✅ فایل دریافت شد. در حال آپلود...")

        # آپلود فایل از روی هارد
        with open(local_path, 'rb') as f:
            await message.reply_document(document=f, caption=f"✅ فایل شما با موفقیت پردازش شد!")

        await status_msg.delete()

    except Exception as e:
        logger.error(f"Error in handle_file: {e}")
        await status_msg.edit_text("❌ خطایی در پردازش فایل رخ داد.")

    finally:
        # پاک کردن فایل از هارد Render برای جلوگیری از پر شدن دیسک
        if 'local_path' in locals() and local_path.exists():
            local_path.unlink()

def main():
    if not TOKEN:
        logger.error("🚨 BOT_TOKEN تنظیم نشده است! ربات روشن نمی‌شود.")
        return

    # ساخت اپلیکیشن
    app = Application.builder().token(TOKEN).build()

    # هندلرها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO | filters.AUDIO, handle_file))

    if RENDER_EXTERNAL_URL:
        # حالت وب‌هوک (مخصوص Render)
        webhook_url = f"{RENDER_EXTERNAL_URL}/{TOKEN}"
        logger.info(f"🚀 Starting Webhook on port {PORT} -> {webhook_url}")
        
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=webhook_url,
        )
    else:
        # حالت لوکال برای تست روی کامپیوتر خودتان
        logger.info("🚀 Starting Polling (Local Mode)")
        app.run_polling()

if __name__ == "__main__":
    main()
