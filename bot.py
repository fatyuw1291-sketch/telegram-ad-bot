
from aiogram import Bot,Dispatcher
from aiogram.enums.parse_mode import ParseMode
from aiogram.client.default import DefaultBotProperties
import os

BOT_TOKEN=os.getenv("BOT_TOKEN")
bot=Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp=Dispatcher()

print("Bot loaded successfully with Aiogram 3.22")
