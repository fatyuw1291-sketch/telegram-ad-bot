# bot.py
# تمام منطق اصلی ربات (ثبت آگهی، FSM، ادمین، دیتابیس) این‌جاست.
import os
import asyncio
import logging
import aiosqlite

from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums.parse_mode import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()  # فقط برای توسعه محلی؛ در Render از Env Vars استفاده کن

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

ADMIN_IDS_ENV = os.getenv("ADMIN_ID", "")  # کاما جدا شده: "123,456"
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "").strip()  # مانند @MyChannel
DB_PATH = os.getenv("DB_PATH", "ads.db")

# parse admin ids
ADMIN_IDS = []
for part in [p.strip() for p in ADMIN_IDS_ENV.split(",") if p.strip()]:
    try:
        ADMIN_IDS.append(int(part))
    except ValueError:
        logger.warning("Ignoring invalid ADMIN_ID value: %s", part)

# Create Bot with new style (fix parse_mode error)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# Dispatcher with MemoryStorage (مثل قبلی)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# FSM
class AdForm(StatesGroup):
    title = State()
    description = State()

# DB init
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            title TEXT,
            description TEXT,
            status TEXT DEFAULT 'pending'
        )""")
        await db.commit()
    logger.info("Initialized DB: %s", DB_PATH)

# /start and open form (preserve texts and buttons from فایل شما)
@dp.message(F.text.in_({"/start", "ثبت_آگهی", "/ثبت_آگهی"}))
async def start_cmd(message: types.Message):
    welcome_text = (
        "👋 به ربات خوش آمدی!\n\n"
        "برای ثبت آگهی روی دکمه زیر بزن."
    )
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(text="📨 ثبت آگهی", callback_data="start_new_ad"))
    await message.answer(welcome_text, reply_markup=kb)

@dp.callback_query(F.data == "start_new_ad")
async def start_new_ad(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    await cb.message.answer("📝 لطفاً عنوان آگهی را وارد کنید:")
    await state.set_state(AdForm.title)

@dp.message(AdForm.title)
async def ad_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AdForm.description)
    await message.answer("🔍 لطفاً توضیحات آگهی را وارد کنید:")

@dp.message(AdForm.description)
async def ad_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    title = data.get("title", "")
    description = message.text
    await state.update_data(description=description)

    final_buttons = InlineKeyboardMarkup(row_width=1)
    final_buttons.add(
        InlineKeyboardButton(text="📨 ثبت نهایی آگهی جهت انتشار در کانال", callback_data="submit_ad"),
        InlineKeyboardButton(text="💬 ارتباط با پشتیبانی", url="https://t.me/Gisonline2")
    )

    text = (
        f"📋 لطفاً اطلاعات آگهی‌ت رو بررسی کن:\n\n"
        f"🏷 عنوان: {title}\n"
        f"📝 توضیحات: {description}\n\n"
        "اگر مورد تاییده، روی ثبت نهایی بزن."
    )
    await message.answer(text, reply_markup=final_buttons)

@dp.callback_query(F.data == "submit_ad")
async def submit_ad(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    data = await state.get_data()
    title = data.get("title", "")
    description = data.get("description", "")
    user = cb.from_user

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

        text_for_admin = (
            f"📢 آگهی جدید برای بررسی:\n\n"
            f"🆔 آیدی: {ad_id}\n"
            f"🏷 عنوان: {title}\n"
            f"📝 توضیحات: {description}\n"
            f"👤 فرستنده: @{user.username or '—'}"
        )
        for admin in ADMIN_IDS:
            try:
                await bot.send_message(admin, text_for_admin, reply_markup=buttons)
            except Exception as e:
                logger.exception("Failed to notify admin %s: %s", admin, e)
        try:
            await bot.send_message(user.id, "✅ آگهی شما ارسال شد و منتظر تأیید مدیر است.")
        except Exception:
            pass
    else:
        await bot.send_message(user.id, "🔔 آگهی شما ثبت شد اما ادمینی برای بررسی تنظیم نشده است.")

    await state.clear()

@dp.callback_query(F.data.regexp(r'^(approve|reject):\d+$'))
async def process_admin_decision(cb: types.CallbackQuery):
    await cb.answer()
    if cb.from_user.id not in ADMIN_IDS:
        return await cb.answer("⛔️ شما مجاز نیستید.", show_alert=True)

    action, ad_id_str = cb.data.split(":")
    try:
        ad_id = int(ad_id_str)
    except ValueError:
        return await cb.answer("⚠️ آیدی نامعتبر.", show_alert=True)

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id, username, title, description FROM ads WHERE id = ?", (ad_id,))
        row = await cur.fetchone()
        if not row:
            return await cb.answer("⚠️ آگهی پیدا نشد.", show_alert=True)

        user_id, username, title, description = row

        if action == "approve":
            await db.execute("UPDATE ads SET status='approved' WHERE id=?", (ad_id,))
            await db.commit()
            post_text = f"📢 آگهی تایید شده:\n\n🏷 {title}\n📝 {description}\n👤 @{username or 'ناشناس'}"
            # Try send to channel if set, else notify admins
            if CHANNEL_USERNAME:
                try:
                    await bot.send_message(CHANNEL_USERNAME, post_text)
                except Exception as e:
                    logger.exception("Failed to post to channel: %s", e)
                    for admin in ADMIN_IDS:
                        await bot.send_message(admin, f"⚠️ خطا در ارسال به کانال: {e}")
            else:
                for admin in ADMIN_IDS:
                    await bot.send_message(admin, post_text)
            try:
                await bot.send_message(user_id, f"✅ آگهی شما (#{ad_id}) تایید و منتشر شد. 🌟")
            except Exception:
                pass
            await cb.answer("✅ تایید شد.")
        else:
            await db.execute("UPDATE ads SET status='rejected' WHERE id=?", (ad_id,))
            await db.commit()
            try:
                await bot.send_message(user_id, f"❌ آگهی شما (#{ad_id}) رد شد.")
            except Exception:
                pass
            await cb.answer("❌ رد شد.")

# on_startup helper (called from web server launcher)
async def on_startup():
    await init_db()
    logger.info("Bot startup completed.")

# on_cleanup helper (if you want cleanup tasks)
async def on_cleanup():
    # close storage/bot if needed
    try:
        await storage.close()
    except Exception:
        pass
    try:
        await bot.session.close()
    except Exception:
        pass
