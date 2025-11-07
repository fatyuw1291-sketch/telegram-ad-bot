# run.py
import os
import threading
from aiohttp import web

# --- این خط‌ها را مطابق ساختار پروژه‌ات تنظیم کن ---
# فرض می‌کنیم dispatcher و راه‌اندازی ربات در bot.py یا دیگری قرار داره
# اگر در bot.py تابع main یا dp تعریف شده، آن را import کن
# مثال: از bot.py فرضی import dispatcher یا تابع start_polling
# برای مثال زیر فرض میکنیم bot.py تابع start_bot() داره که polling رو اجرا میکنه.
# اگر کدت فرق داره، بخش زیر را مطابق کدت تغییر بده.
try:
    # اگر در bot.py تابع start_polling مشخص نیست، این بخش را متناسب با ساختارت تغییر بده
    from bot import start_polling  # تابعی که polling را اجرا می‌کند
except Exception:
    # اگر توی bot.py تابعی برای start نذاشتی، این یک نمونه‌ی عمومی برای aiogram است:
    def start_polling():
        # اگر از aiogram استفاده می‌کنی و dp را در bot.py داری:
        # from aiogram import executor
        # from bot import dp
        # executor.start_polling(dp, skip_updates=True)
        raise RuntimeError("لطفاً تابع start_polling را در bot.py بساز یا این import را اصلاح کن.")

# تابعی که polling را در ترد جدا اجرا می‌کند
def _start_bot_thread():
    try:
        start_polling()
    except Exception as e:
        print("Error in start_polling:", e)

# یک HTTP handler ساده (برای Render)
async def handle_root(request):
    return web.Response(text="Bot is running\n")

def run_webserver():
    app = web.Application()
    app.router.add_get('/', handle_root)
    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)

if name == "main":
    # 1. راه‌اندازی ربات در ترد جدا
    t = threading.Thread(target=_start_bot_thread, daemon=True)
    t.start()

    # 2. راه‌اندازی وب‌سرور (این پورت برای Render قابل اسکن است)
    print("Starting webserver on port", os.environ.get("PORT", "10000"))
    run_webserver()