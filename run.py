import os
import threading
from bot import start_bot
from flask import Flask

# وب‌سرور ساده برای Render
app = Flask(name)

@app.route('/')
def home():
    return "Bot is running successfully!"

def run_webserver():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def _start_bot_thread():
    # اجرای ربات در یک ترد جدا
    start_bot()

if name == "main":
    # اجرای ربات
    t = threading.Thread(target=_start_bot_thread, daemon=True)
    t.start()

    # اجرای وب‌سرور
    print("Starting webserver on port", os.environ.get("PORT", "10000"))
    run_webserver()