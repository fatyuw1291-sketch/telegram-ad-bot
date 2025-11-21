
import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums.parse_mode import ParseMode
from aiohttp import web
import aiosqlite

# Load environment variables from Render
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_ID","").split(",") if x.strip().isdigit()]
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME","").strip()
PUBLIC_URL = os.getenv("PUBLIC_URL")
PING_INTERVAL = int(os.getenv("PING_INTERVAL_SECONDS", "600"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())
DB_PATH = "ads.db"

class AdForm(StatesGroup):
    title = State()
    description = State()

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            title TEXT,
            description TEXT,
            status TEXT DEFAULT 'pending'
        )
        """)
        await db.commit()

@dp.message(F.text.in_({"/start","/ثبت_آگهی"}))
async def start_cmd(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📨 ثبت آگهی", callback_data="start_new_ad")]
    ])
    await message.answer("👋 به ربات خوش آمدی\nبرای ثبت آگهی روی دکمه زیر بزن.", reply_markup=kb)

@dp.callback_query(F.data == "start_new_ad")
async def cb_start_new_ad(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer("📝 لطفاً عنوان آگهی را وارد کنید:")
    await state.set_state(AdForm.title)

@dp.message(AdForm.title)
async def form_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AdForm.description)
    await message.answer("🔍 لطفاً توضیحات آگهی را وارد کنید:")

@dp.message(AdForm.description)
async def form_description(message: Message, state: FSMContext):
    data = await state.get_data()
    title = data["title"]
    desc = message.text
    await state.update_data(description=desc)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📨 ثبت نهایی", callback_data="submit_ad")],
        [InlineKeyboardButton(text="💬 پشتیبانی", url="https://t.me/Gisonline2")]
    ])

    await message.answer(
        f"📝 <b>بررسی اطلاعات آگهی:</b>\n\n"
        f"🏷 <b>عنوان:</b> {title}\n"
        f"📝 <b>توضیحات:</b> {desc}\n\n"
        "اگر تایید است، روی ثبت نهایی بزن.",
        reply_markup=kb
    )

@dp.callback_query(F.data == "submit_ad")
async def finish_ad(cb: CallbackQuery, state: FSMContext):
    user = cb.from_user
    data = await state.get_data()
    title = data["title"]
    desc = data["description"]

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO ads (user_id, username, title, description) VALUES (?, ?, ?, ?)",
            (user.id, user.username or "", title, desc)
        )
        await db.commit()
        cur = await db.execute("SELECT last_insert_rowid()")
        ad_id = (await cur.fetchone())[0]

    if ADMIN_IDS:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ تایید", callback_data=f"approve:{ad_id}"),
                InlineKeyboardButton(text="❌ رد", callback_data=f"reject:{ad_id}")
            ]
        ])

        text = (
            f"📢 <b>آگهی جدید:</b>\n\n"
            f"🆔 ID: {ad_id}\n"
            f"🏷 {title}\n"
            f"📝 {desc}\n"
            f"👤 @{user.username or '—'}"
        )

        for admin in ADMIN_IDS:
            await bot.send_message(admin, text, reply_markup=kb)

    await cb.message.answer("✅ آگهی شما ارسال شد. منتظر تایید مدیر باشید.")
    await state.clear()

@dp.callback_query(F.data.startswith(("approve","reject")))
async def admin_actions(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        return await cb.answer("⛔ دسترسی ندارید", show_alert=True)

    action, ad_id = cb.data.split(":")

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id, username, title, description FROM ads WHERE id=?", (ad_id,))
        row = await cur.fetchone()

        if not row:
            return await cb.answer("آگهی یافت نشد")

        user_id, user, title, desc = row

        if action == "approve":
            await db.execute("UPDATE ads SET status='approved' WHERE id=?", (ad_id,))
            await db.commit()

            post = f"📢 <b>آگهی تایید شده:</b>\n\n🏷 {title}\n📝 {desc}\n👤 @{user or 'ناشناس'}"
            if CHANNEL_USERNAME:
                await bot.send_message(CHANNEL_USERNAME, post)

            await bot.send_message(user_id, f"✅ آگهی شما تایید و منتشر شد.")
            await cb.answer("✔️ تایید شد")

        else:
            await db.execute("UPDATE ads SET status='rejected' WHERE id=?", (ad_id,))
            await db.commit()
            await bot.send_message(user_id, f"❌ آگهی شما رد شد.")
            await cb.answer("❌ رد شد")

async def self_ping():
    if not PUBLIC_URL:
        return
    import aiohttp
    while True:
        try:
            async with aiohttp.ClientSession() as s:
                await s.get(PUBLIC_URL + "/ping")
        except:
            pass
        await asyncio.sleep(PING_INTERVAL)

async def start_bot():
    await init_db()
    asyncio.create_task(self_ping())
    await dp.start_polling(bot)

async def handle_ping(request):
    return web.Response(text="ok")

def create_app():
    app = web.Application()
    app.router.add_get("/ping", handle_ping)
    app.on_startup.append(lambda app: asyncio.create_task(start_bot()))
    return app

if __name__ == "__main__":
    web.run_app(create_app(), host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
