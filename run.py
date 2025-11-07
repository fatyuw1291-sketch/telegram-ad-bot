import os
import asyncio
from flask import Flask
from aiogram import Bot, Dispatcher, executor
from dotenv import load_dotenv

# 🔹 بارگذاری توکن از فایل .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# 🔹 راه‌اندازی Flask برای سرویس وب Render
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Telegram bot is running successfully on Render!"

# 🔹 راه‌اندازی Aiogram Bot
from bot import dp, bot  # توجه: فایل bot.py باید شامل Bot و Dispatcher باشد

async def on_startup(_):
    print("🤖 Bot started successfully and connected to Telegram API!")

if __name__ == "__main__":
    # اجرای هم‌زمان Flask و Aiogram
    loop = asyncio.get_event_loop()
    loop.create_task(executor.start_polling(dp, skip_updates=True, on_startup=on_startup))
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
