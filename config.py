import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@Macetfinance").strip()
TELEGRAM_CHANNEL_USERNAME = os.getenv("TELEGRAM_CHANNEL_USERNAME", "@Macetfinance").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
AUTO_NEWS_INTERVAL_SECONDS = int(os.getenv("AUTO_NEWS_INTERVAL_SECONDS", "300"))

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("Chưa thiết lập TELEGRAM_BOT_TOKEN trong file .env!")
