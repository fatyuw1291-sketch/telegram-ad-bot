
# Deploy to Render (step-by-step)

1. Create a new **Web Service** on Render and connect your GitHub repository.
2. Build Command: leave empty (or set if you need). Start Command: `python bot.py`
3. Environment variables (set these in Render dashboard -> Environment):
   - `TELEGRAM_TOKEN` = your bot token
   - `ADMIN_IDS` = comma-separated admin Telegram IDs (if your code uses it)
   - `PUBLIC_URL` = the public URL of your Render service (e.g. `https://my-bot.onrender.com`) — **important** for keepalive pings
   - Any other vars your bot needs (DB path, etc.)
4. Make sure Procfile (or start command) runs `python bot.py`. We included a `web: python bot.py` Procfile.
5. Deploy. The service will expose `/ping` and the bot will run via long-polling in the background.
6. The bot contains a periodic self-ping (PING_INTERVAL_SECONDS) that will call `PUBLIC_URL/ping` every `PING_INTERVAL_SECONDS` seconds to help keep the service awake.
   - If you prefer not to use self-ping, leave `PUBLIC_URL` empty.
7. Note: Render may still suspend services for inactivity if you exceed free-tier limits or policies. This self-ping helps but is not a guaranteed workaround of provider limits or terms of service.

