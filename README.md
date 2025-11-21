# Telegram Ad Bot (Railway-ready)

This repository contains a Telegram bot to collect project ads and publish them after admin approval.
Prepared for deployment on Railway.

## Files included
- `bot.py` — main bot code (reads configuration from environment variables)
- `requirements.txt` — Python dependencies
- `Procfile` — start command (optional for Railway)
- `.env.example` — sample environment variables (DO NOT commit real secrets)
- `.gitignore` — files to ignore

## Environment variables (set these in Railway -> Project -> Variables)
- `BOT_TOKEN` = your Telegram bot token (from BotFather)
- `ADMIN_ID` = comma-separated admin numeric Telegram IDs (e.g. 6693134557,351326880)
- `CHANNEL_USERNAME` = optional channel username (e.g. @GEProjects)

## Deploy on Railway
1. Push this repo to GitHub.
2. Create a new project on Railway and choose "Deploy from GitHub".
3. Select this repo.
4. In Railway project settings -> Variables, add BOT_TOKEN, ADMIN_ID, CHANNEL_USERNAME.
5. Ensure start command is: `python bot.py`
6. Deploy. Check logs for "🤖 ربات پروژه فوری در حال اجراست..."

## Important security note
- **Do NOT** put your real `BOT_TOKEN` inside the repository. Use Railway environment variables.
- If you accidentally exposed your token, rotate it in BotFather immediately.
