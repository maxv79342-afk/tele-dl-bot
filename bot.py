#!/usr/bin/env python3
import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

# خواندن متغیرهای محیطی
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# پوشه دانلود
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ساخت کلاینت Pyrogram
app = Client(
    "render_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workdir=DOWNLOAD_DIR
)

@app.on_message(filters.command("start") & filters.private)
async def start(client: Client, message: Message):
    await message.reply_text("سلام! من یک ربات دانلودر حرفه‌ای هستم. فایل یا ویدیو را بفرست تا آن را پردازش کنم.")

@app.on_message(filters.document | filters.video | filters.audio | filters.photo & filters.private)
async def download_and_process(client: Client, message: Message):
    # پیدا کردن فایل
    media = message.document or message.video or message.audio or message.photo
    
    if not media:
        return

    status_msg = await message.reply_text("⏳ در حال دانلود فایل...")

    try:
        # دانلود فایل (Pyrogram به صورت قطعه‌قطعه دانلود می‌کند که رم کمتری می‌گیرد)
        file_path = await client.download_media(
            message,
            file_name=f"{DOWNLOAD_DIR}/{media.file_unique_id}"
        )
        
        await status_msg.edit_text("✅ دانلود شد. در حال آپلود...")
        
        # آپلود فایل (حمایت از فایل‌های تا 2 گیگابایت)
        await message.reply_document(
            document=file_path,
            caption=f"✅ فایل شما با موفقیت پردازش شد."
        )
        
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit_text(f"❌ خطا در پردازش فایل: {str(e)}")
    
    finally:
        # بسیار مهم: پاک کردن فایل از سرور برای جلوگیری از پر شدن دیسک Render
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    print("Bot is starting...")
    app.run()
