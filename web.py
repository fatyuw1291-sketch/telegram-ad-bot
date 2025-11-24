# web.py
from aiohttp import web
import os
import asyncio
import logging
from bot import on_startup, on_cleanup, dp, bot

logger = logging.getLogger(name)

PUBLIC_URL = os.getenv("PUBLIC_URL", "").rstrip("/")
PING_INTERVAL = int(os.getenv("PING_INTERVAL_SECONDS", "600"))

async def handle_ping(request):
    return web.Response(text="ok")

async def start_background_tasks(app):
    # init bot/db
    await on_startup()

    # start aiogram polling in background
    # dp.start_polling(bot) will run until cancelled
    app['bot_task'] = asyncio.create_task(dp.start_polling(bot))

    # self-pinger (optional) to keep Render web service alive by pinging PUBLIC_URL
    if PUBLIC_URL:
        async def pinger():
            import aiohttp
            while True:
                try:
                    async with aiohttp.ClientSession() as session:
                        ping_url = PUBLIC_URL + "/ping"
                        await session.get(ping_url, timeout=15)
                except Exception as e:
                    logger.exception("Self-ping failed: %s", e)
                await asyncio.sleep(PING_INTERVAL)
        app['pinger'] = asyncio.create_task(pinger())

async def cleanup_background_tasks(app):
    # cancel pinger and bot_task gracefully
    if app.get('pinger'):
        app['pinger'].cancel()
    if app.get('bot_task'):
        app['bot_task'].cancel()
        try:
            await app['bot_task']
        except asyncio.CancelledError:
            pass
    await on_cleanup()

def create_app():
    app = web.Application()
    app.router.add_get('/ping', handle_ping)
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    return app

# if you run web.py directly (not necessary, main.py will use it)
if name == "main":
    app = create_app()
    port = int(os.getenv("PORT", 8000))
    web.run_app(app, host="0.0.0.0", port=port)