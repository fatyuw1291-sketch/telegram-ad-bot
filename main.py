# main.py
# entrypoint for Render (Web Service). This runs aiohttp app which also runs dp.start_polling in background.
from web import create_app
from aiohttp import web
import os

if name == "main":
    app = create_app()
    port = int(os.getenv("PORT", 8000))
    # Render sets PORT env var; use it
    web.run_app(app, host="0.0.0.0", port=port)