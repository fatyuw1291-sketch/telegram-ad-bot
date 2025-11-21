# -*- coding: utf-8 -*-
import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from dotenv import load_dotenv
import aiosqlite

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment (for local dev). In production (Railway) set env vars in project settings.
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS_ENV = os.getenv("ADMIN_ID", "")  # comma separated list of numeric IDs
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "")  # e.g. @MyChannel

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Add BOT_TOKEN in environment variables (Railway/Project → Variables).")

# Parse admin ids
ADMIN_IDS = []
for part in [p.strip() for p in ADMIN_IDS_ENV.split(",") if p.strip()]:
    try:
        ADMIN_IDS.append(int(part))
    except ValueError:
        logger.warning("Ignoring invalid ADMIN_ID value: %s", part)

if not ADMIN_IDS:
    logger.warning("No ADMIN_ID configured. Admin actions will be disabled until ADMIN_IDs are set.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
DB_PATH = "ads.db"

class AdForm(StatesGroup):
    title = State()
    description = State()

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(\"\"\"CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            title TEXT,
            description TEXT,
            status TEXT DEFAULT 'pending'
        )\"\"\")
        await db.commit()
    logger.info("Initialized database: %s", DB_PATH)

@dp.message_handler(commands=['start', 'ثبت_آگهی'])
async def start_cmd(message: types.Message):
    welcome_text = (
        "👋 به پروژه فوری خوش اومدی!\n\n"
        "درخواست خودت رو ثبت کن ✍️\n\n"
        "برای شروع روی دکمه زیر بزن."
    )
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton(text="📨 ثبت آگهی", callback_data="start_new_ad")
    )
    await message.answer(welcome_text, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "start_new_ad")
async def start_new_ad(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await bot.send_message(callback.from_user.id, "📝 لطفاً عنوان پروژه را بنویس:")
    await AdForm.title.set()

@dp.message_handler(state=AdForm.title)
async def ad_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("🔍 لطفاً توضیحات پروژه‌ت رو بنویس:")
    await AdForm.description.set()

@dp.message_handler(state=AdForm.description)
async def ad_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    title = data.get("title", "")
    description = message.text
    await state.update_data(description=description)

    final_buttons = InlineKeyboardMarkup(row_width=1)
    final_buttons.add(
        InlineKeyboardButton(text="📨 ثبت نهایی آگهی جهت انتشار در کانال", callback_data="submit_ad"),
        InlineKeyboardButton(text="💬 ارتباط بیشتر با ادمین پشتیبانی", url="https://t.me/Gisonline2")
    )

    text = (
        f"📋 لطفاً اطلاعات آگهی‌ت رو بررسی کن:\n\n"
        f"🏷 عنوان: {title}\n"
        f"📝 توضیحات: {description}\n\n"
        "اگر مورد تأییده، روی «ثبت نهایی آگهی جهت انتشار در کانال» بزن."
    )
    await message.answer(text, reply_markup=final_buttons)

@dp.callback_query_handler(lambda c: c.data == "submit_ad")
async def submit_ad(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    title = data.get("title", "")
    description = data.get("description", "")
    user = callback.from_user

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO ads (user_id, username, title, description) VALUES (?, ?, ?, ?)",
            (user.id, user.username or "", title, description)
        )
        await db.commit()
        cur = await db.execute("SELECT last_insert_rowid()")
        row = await cur.fetchone()
        ad_id = row[0] if row else None

    if ADMIN_IDS:
        buttons = InlineKeyboardMarkup(row_width=2)
        buttons.add(
            InlineKeyboardButton(text="✅ تأیید", callback_data=f"approve:{ad_id}"),
            InlineKeyboardButton(text="❌ رد", callback_data=f"reject:{ad_id}")
        )

        text = (
            f"📢 آگهی جدید برای بررسی:\n\n"
            f"🆔 آیدی: {ad_id}\n"
            f"🏷 عنوان: {title}\n"
            f"📝 توضیحات: {description}\n"
            f"👤 فرستنده: @{user.username or '—'}"
        )
        for admin in ADMIN_IDS:
            try:
                await bot.send_message(admin, text, reply_markup=buttons)
            except Exception as e:
                logger.exception("Failed to notify admin %s: %s", admin, e)
        await bot.send_message(callback.from_user.id, "✅ آگهی شما ارسال شد و منتظر تأیید مدیر است.")
    else:
        await bot.send_message(callback.from_user.id, "🔔 آگهی شما ثبت شد اما ادمینی برای بررسی تنظیم نشده است.")

    await state.finish()

@dp.callback_query_handler(lambda c: c.data and (c.data.startswith("approve:") or c.data.startswith("reject:")))
async def process_admin_decision(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return await callback.answer("⛔ شما مجاز نیستید.", show_alert=True)

    action, ad_id_str = callback.data.split(":")
    try:
        ad_id = int(ad_id_str)
    except ValueError:
        return await callback.answer("⚠️ آیدی نامعتبر.", show_alert=True)

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id, username, title, description FROM ads WHERE id = ?", (ad_id,))
        row = await cur.fetchone()
        if not row:
            return await callback.answer("⚠️ آگهی پیدا نشد.", show_alert=True)

        user_id, username, title, description = row

        if action == "approve":
            await db.execute("UPDATE ads SET status='approved' WHERE id=?", (ad_id,))
            await db.commit()
            post_text = f"📢 آگهی تایید شده:\n\n🏷 {title}\n📝 {description}\n👤 @{username or 'ناشناس'}"
            if CHANNEL_USERNAME:
                try:
                    await bot.send_message(CHANNEL_USERNAME, post_text)
                except Exception as e:
                    for admin in ADMIN_IDS:
                        await bot.send_message(admin, f"⚠️ خطا در ارسال به کانال: {e}")
            else:
                for admin in ADMIN_IDS:
                    await bot.send_message(admin, post_text)
            try:
                await bot.send_message(user_id, f"✅ آگهی شما (#{ad_id}) تایید و منتشر شد. 🌟")
            except:
                pass
            await callback.answer("✅ تایید شد.")
        else:
            await db.execute("UPDATE ads SET status='rejected' WHERE id=?", (ad_id,))
            await db.commit()
            try:
                await bot.send_message(user_id, f"❌ آگهی شما (#{ad_id}) رد شد.")
            except:
                pass
            await callback.answer("❌ رد شد.")

async def on_startup(_):
    await init_db()
    print("🤖 ربات پروژه فوری در حال اجراست...")

if __name__ == "__main__":
    # When running locally for development, use normal polling
    # For Render deployment we start an aiohttp web server and run polling in background
    try:
        from aiohttp import web
    except Exception as e:
        print("aiohttp not available:", e)
        # fallback to polling
        executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
    else:
        async def handle_ping(request):
            return web.Response(text="ok")

        async def start_background_tasks(app):
            # initialize DB and other startup actions
            await on_startup(app)

            # start aiogram polling in background
            app['bot_task'] = asyncio.create_task(dp.start_polling())

            # self-pinger to keep the service awake: set PUBLIC_URL env var to your render URL (https://your-service.onrender.com)
            PUBLIC_URL = os.getenv('PUBLIC_URL')
            PING_INTERVAL = int(os.getenv('PING_INTERVAL_SECONDS', '600'))  # default 10 minutes
            if PUBLIC_URL:
                async def pinger():
                    import aiohttp as _aiohttp
                    while True:
                        try:
                            async with _aiohttp.ClientSession() as session:
                                ping_url = PUBLIC_URL.rstrip('/') + '/ping'
                                await session.get(ping_url, timeout=15)
                        except Exception as e:
                            logger.exception("Self-ping failed: %s", e)
                        await asyncio.sleep(PING_INTERVAL)
                app['pinger'] = asyncio.create_task(pinger())

        async def cleanup_background_tasks(app):
            # cancel background tasks gracefully
            if app.get('pinger'):
                app['pinger'].cancel()
            if app.get('bot_task'):
                app['bot_task'].cancel()
                try:
                    await app['bot_task']
                except asyncio.CancelledError:
                    pass

        app = web.Application()
        app.router.add_get('/ping', handle_ping)
        app.on_startup.append(start_background_tasks)
        app.on_cleanup.append(cleanup_background_tasks)

        port = int(os.getenv('PORT', 8000))
        print(f"Starting web server on 0.0.0.0:{port} ...")
        web.run_app(app, host='0.0.0.0', port=port)
