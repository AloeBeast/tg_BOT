import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
AI_API_KEY = os.getenv("AI_API_KEY")
AI_BASE_URL = os.getenv("AI_BASE_URL")
AI_MODEL = "gemini-3.1-flash-lite"        # основная модель — для диалога с Виктором
AI_MODEL_FAST = "DeepSeek V4 Flash"   # модель для рутинных задач (извлечение фактов и т.п.)
AI_MODEL_VISION = AI_MODEL  # используем ту же модель, что и для диалога — Gemini умеет в зрение

if not BOT_TOKEN or not AI_API_KEY or not AI_BASE_URL:
    raise ValueError("Не найдены BOT_TOKEN / AI_API_KEY / AI_BASE_URL. Проверь файл .env")