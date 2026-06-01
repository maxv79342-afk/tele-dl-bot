#!/usr/bin/env python3
import os
import logging
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# فعال‌سازی لاگ‌گیری برای دیباگ در Render
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# متغیرهای محیطی
TOKEN = os.getenv("BOT_TOKEN")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.getenv("PORT", "8000"))

# پوشه دانلود
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! من ربات دانلودر هستم.\n"
        "⚠️ توجه: به دلیل محدودیت‌های تلگرام، فقط فایل‌های تا ۲۰ مگابایت قابل دانلود و ۵۰ مگابایت قابل آپلود هستند."
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دانلود فایل روی هارد سرور و آپلود مجدد آن (بدون مصرف رم)"""
    message = update.message
    doc = message.document or message.video or message.audio or message.photo
    
    if not doc:
        return

    # محدودیت حجم فایل برای دانلود (20MB)
    file_size_mb = doc.file_size / (1024 * 1024)
    if file_size_mb > 20:
        await message.reply_text("❌ حجم فایل بیشتر از ۲۰ مگابایت است. دانلود در API معمولی تلگرام ممکن نیست.")
        return

    status_msg = await message.reply_text("⏳ در حال دانلود فایل روی سرور...")

    try:
        # دریافت اطلاعات فایل
        telegram_file = await context.bot.get_file(doc.file_id)
        
        # ساخت مسیر ذخیره روی هارد
        file_name = getattr(doc, 'file_name', None) or f"{doc.file_unique_id}.dat"
        local_path = DOWNLOAD_DIR / file_name

        # دانلود مستقیم روی هارد (بدون اشغال رم - بسیار مهم برای Render)
        await telegram_file.download_to_drive(custom_path=str(local_path))

        await status_msg.edit_text("✅ دانلود شد. در حال آپلود...")

        # آپلود فایل از روی هارد
        with open(local_path, 'rb') as f:
            await message.reply_document(document=f, caption=f"✅ فایل شما ({file_name})")

        await status_msg.delete()

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        await status_msg.edit_text(f"❌ خطا در پردازش فایل: {str(e)[:100]}")

    finally:
        # بسیار مهم: پاک کردن فایل از هارد سرور برای جلوگیری از پر شدن دیسک Render
        if 'local_path' in locals() and local_path.exists():
            local_path.unlink()

def main():
    """اجرای ربات با وب‌هوک برای Render"""
    if not TOKEN:
        logger.error("BOT_TOKEN تنظیم نشده است!")
        return

    # ساخت اپلیکیشن
    app = Application.builder().token(TOKEN).build()

    # هندلرها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO | filters.AUDIO | filters.PHOTO, handle_document))

    if RENDER_EXTERNAL_URL:
        # اجرا روی Render با Webhook
        webhook_url = f"{RENDER_EXTERNAL_URL}/{TOKEN}"
        logger.info(f"Starting webhook on {webhook_url}")
        
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=webhook_url
        )
    else:
        # اجرا در سیستم محلی (Local) با Polling برای تست
        logger.info("Starting polling (local mode)")
        app.run_polling()

if __name__ == "__main__":
    main()
