import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from dotenv import load_dotenv
import aiosqlite

# 🔹 بارگذاری تنظیمات از فایل .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_ID", "6693134557,351326880").split(",")]
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@GEProjects")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
DB_PATH = "ads.db"


# 🔹 مراحل ثبت آگهی
class AdForm(StatesGroup):
    title = State()
    description = State()


# 🔹 ساخت دیتابیس در اولین اجرا
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


# 🔹 پیام خوش‌آمد
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    welcome_text = "👋 به پروژه فوری خوش اومدی!\n📌 آگهی پروژه یا درخواست خودت رو ثبت کن ✍️"
    start_buttons = InlineKeyboardMarkup().add(
        InlineKeyboardButton(text="📨 ثبت آگهی", callback_data="start_new_ad")
    )
    await message.answer(welcome_text, reply_markup=start_buttons)


# 🔹 شروع ثبت آگهی با فشردن دکمه
@dp.callback_query_handler(lambda c: c.data == "start_new_ad")
async def start_new_ad(callback: types.CallbackQuery):
    await bot.send_message(callback.from_user.id, "📝 لطفاً عنوان پروژه رو بنویس:")
    await AdForm.title.set()


# 🔹 دریافت عنوان پروژه
@dp.message_handler(state=AdForm.title)
async def ad_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("🔍 لطفاً توضیحات پروژه‌ت رو بنویس:")
    await AdForm.description.set()


# 🔹 مرحله آخر: بررسی اطلاعات + گزینه ثبت نهایی
@dp.message_handler(state=AdForm.description)
async def ad_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    title = data["title"]
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
        f"اگر مورد تأییدته، روی «ثبت نهایی آگهی جهت انتشار در کانال» بزن."
    )
    await message.answer(text, reply_markup=final_buttons)


# 🔹 وقتی کاربر روی "ثبت نهایی" می‌زند
@dp.callback_query_handler(lambda c: c.data == "submit_ad")
async def submit_ad(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    title = data["title"]
    description = data["description"]
    user = callback.from_user
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO ads (user_id, username, title, description) VALUES (?, ?, ?, ?)",
            (user.id, user.username or "", title, description)
        )
        await db.commit()
        cur = await db.execute("SELECT last_insert_rowid()")
        ad_id = (await cur.fetchone())[0]

    # ارسال برای همه ادمین‌ها جهت بررسی
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
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, reply_markup=buttons)
        except:
            pass
    await bot.send_message(callback.from_user.id, "✅ آگهی شما ارسال شد و منتظر تأیید مدیر است.")
    await state.finish()


# 🔹 تأیید یا رد آگهی توسط مدیران
@dp.callback_query_handler(lambda c: c.data and c.data.startswith(("approve:", "reject:")))
async def process_admin_decision(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return await callback.answer("⛔️ شما مجاز نیستید.", show_alert=True)

    action, ad_id_str = callback.data.split(":")
    ad_id = int(ad_id_str)

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
                    for admin_id in ADMIN_IDS:
                        await bot.send_message(admin_id, f"⚠️ خطا در ارسال به کانال: {e}")
            else:
                for admin_id in ADMIN_IDS:
                    await bot.send_message(admin_id, post_text)
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


# 🔹 تابع مخصوص Render برای اجرای ربات
def start_bot():
    async def main():
        await init_db()
        print("🤖 ربات پروژه فوری در حال اجراست...")
        await dp.start_polling()

    asyncio.run(main())