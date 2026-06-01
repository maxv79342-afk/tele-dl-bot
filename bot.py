#!/usr/bin/env python3
import os
import logging
import traceback
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# تنظیمات لاگ‌گیری پیشرفته برای Render
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# توکن هاردکد شده
TOKEN = "8137662462:AAGJ_u9tXdQjgR5YG9JxlO_kdVRj7sNENy4"
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.getenv("PORT", "10000"))

# پوشه دانلود
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# ==========================================================
# ارور هندلر بسیار مهم: اگر جایی ارور داد، به شما پیام میده
# ==========================================================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)
    if update and isinstance(update, Update) and update.effective_message:
        error_msg = str(context.error)[:200] # فقط 200 کاراکتر اول ارور
        await update.effective_message.reply_text(
            f"⚠️ خطای سیستمی رخ داد:\n`{error_msg}`",
            parse_mode="Markdown"
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} started the bot")
    await update.message.reply_text(
        "👋 سلام! من ربات پردازش فایل هستم.\n\n"
        "یک فایل، ویدیو یا صدا بفرستید.\n"
        "⚠️ محدودیت: فقط فایل‌های **زیر ۲۰ مگابایت** (قانون تلگرام)."
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Received file from {update.effective_user.id}")
    message = update.message
    
    # استخراج امن فایل (بدون ارور)
    doc = message.document or message.video or message.audio or message.animation
    
    if not doc:
        await message.reply_text("⚠️ لطفاً فقط فایل، ویدیو یا صدا ارسال کنید. (عکس معمولی پشتیبانی نمی‌شود)")
        return

    # بررسی حجم به صورت امن
    file_size_bytes = getattr(doc, 'file_size', 0)
    file_size_mb = file_size_bytes / (1024 * 1024)
    
    if file_size_mb > 20:
        await message.reply_text(f"❌ حجم فایل {file_size_mb:.1f} مگابایت است.\nفایل‌های بالای ۲۰ مگابایت قابل دانلود نیستند.")
        return

    status_msg = await message.reply_text("⏳ در حال دریافت فایل...")

    local_path = None # تعریف متغیر برای جلوگیری از ارور در finally
    try:
        # دریافت فایل
        telegram_file = await context.bot.get_file(doc.file_id)
        
        # نام‌گذاری امن
        file_name = getattr(doc, 'file_name', None) 
        if not file_name:
            file_name = f"{doc.file_unique_id}.dat"
            
        local_path = DOWNLOAD_DIR / file_name

        # دانلود روی هارد
        await telegram_file.download_to_drive(custom_path=str(local_path))
        await status_msg.edit_text("✅ فایل دریافت شد. در حال آپلود...")

        # آپلود فایل
        with open(local_path, 'rb') as f:
            await message.reply_document(document=f, caption="✅ فایل شما با موفقیت پردازش شد!")
            
        await status_msg.delete()

    except Exception as e:
        logger.error(f"Error in handle_file: {traceback.format_exc()}")
        await status_msg.edit_text(f"❌ خطا در پردازش فایل:\n`{str(e)[:100]}`", parse_mode="Markdown")

    finally:
        # پاک کردن فایل از هارد Render
        if local_path and local_path.exists():
            local_path.unlink()

def main():
    if not TOKEN:
        logger.error("🚨 BOT_TOKEN تنظیم نشده است!")
        return

    # ساخت اپلیکیشن
    app = Application.builder().token(TOKEN).build()

    # افزودن ارور هندلر (بسیار مهم)
    app.add_error_handler(error_handler)

    # هندلرها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(
        filters.Document.ALL | filters.VIDEO | filters.AUDIO | filters.ANIMATION, 
        handle_file
    ))

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
        # حالت لوکال
        logger.info("🚀 Starting Polling (Local Mode)")
        app.run_polling()

if __name__ == "__main__":
    main()
