# run.py — exact file to use on Render (Web Service)
import os
import threading
import traceback
from flask import Flask

# ایمپورت تابعی که در bot.py ساخته‌ایم و ربات را start می‌کند
# توجه: در bot.py باید تابع start_bot() موجود باشد (همان‌طور که قبلاً اصلاح شد).
from bot import start_bot

app = Flask(name)

@app.route("/")
def home():
    return "🤖 Bot is running successfully!"

def _run_bot_thread():
    try:
        print("Thread: starting bot...")
        # start_bot ممکن است از asyncio.run(...) استفاده کند — اجرا در ترد جدا امن است
        start_bot()
    except Exception:
        print("Error while running bot thread:")
        traceback.print_exc()

if name == "main":
    # 1) بوت را در یک ترد جدا اجرا می‌کنیم (daemon تا با بسته شدن پروسه متوقف شود)
    t = threading.Thread(target=_run_bot_thread, daemon=True)
    t.start()

    # 2) وب‌سرور Flask را روی پورتی که Render به کانتینر می‌دهد اجرا می‌کنیم
    port = int(os.environ.get("PORT", 10000))
    print(f"Starting Flask webserver on 0.0.0.0:{port}")
    # نکته: debug=False پیش‌فرض امن‌تر است
    app.run(host="0.0.0.0", port=port)