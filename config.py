import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
AI_API_KEY = os.getenv("AI_API_KEY")
AI_BASE_URL = os.getenv("AI_BASE_URL")
AI_MODEL = os.getenv("AI_MODEL", "gemini-3.1-flash-lite")
AI_MODEL_FAST = os.getenv("AI_MODEL_FAST", AI_MODEL)
AI_MODEL_VISION = os.getenv("AI_MODEL_VISION", AI_MODEL)
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() in {"1", "true", "yes", "on"}
HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", "8"))

if not BOT_TOKEN or not AI_API_KEY or not AI_BASE_URL:
    raise ValueError("Не найдены BOT_TOKEN / AI_API_KEY / AI_BASE_URL. Проверь файл .env")

AI_CHAT_TIMEOUT_SECONDS = float(os.getenv("AI_CHAT_TIMEOUT_SECONDS", "30"))
AI_VISION_TIMEOUT_SECONDS = float(os.getenv("AI_VISION_TIMEOUT_SECONDS", "30"))
AI_RETRY_COUNT = int(os.getenv("AI_RETRY_COUNT", "1"))
PHOTO_RATE_LIMIT_SECONDS = float(os.getenv("PHOTO_RATE_LIMIT_SECONDS", "15"))
MIN_IMAGE_BYTES = int(os.getenv("MIN_IMAGE_BYTES", "10240"))
MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", "5242880"))
VISION_CACHE_MAX_ITEMS = int(os.getenv("VISION_CACHE_MAX_ITEMS", "256"))
