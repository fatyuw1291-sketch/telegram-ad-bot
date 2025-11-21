# Telegram Bot (Aiogram 3 – Render Ready)

## How to Deploy on Render

1. Upload all files to GitHub
2. Create a new *Web Service* on Render
3. Set Start Command:
```
python bot.py
```
4. Add Environment Variables:
- BOT_TOKEN
- ADMIN_ID
- CHANNEL_USERNAME
- PUBLIC_URL
- PING_INTERVAL_SECONDS = 600

Bot auto-pings itself → stays 24/7 alive.
