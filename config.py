import os

from dotenv import load_dotenv

load_dotenv()

<<<<<<< Updated upstream

def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Не найдена переменная окружения {name}. Проверь файл .env")
    return value


def _get_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"Переменная {name} должна быть целым числом, сейчас: {raw_value!r}") from exc


def _get_float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name, str(default))
    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError(f"Переменная {name} должна быть числом, сейчас: {raw_value!r}") from exc


BOT_TOKEN = _get_required_env("BOT_TOKEN")
AI_API_KEY = _get_required_env("AI_API_KEY")
AI_BASE_URL = _get_required_env("AI_BASE_URL")
AI_MODEL = os.getenv("AI_MODEL", "glm-5v-turbo")
=======
BOT_TOKEN = os.getenv("BOT_TOKEN")
AI_API_KEY = os.getenv("AI_API_KEY")
AI_BASE_URL = os.getenv("AI_BASE_URL")
AI_MODEL = "qwen3.7-plus"
>>>>>>> Stashed changes
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() in {"1", "true", "yes", "on"}
HISTORY_LIMIT = _get_int_env("HISTORY_LIMIT", 8)
AI_CHAT_TIMEOUT_SECONDS = _get_float_env("AI_CHAT_TIMEOUT_SECONDS", 30)
AI_RETRY_COUNT = _get_int_env("AI_RETRY_COUNT", 1)
PHOTO_RATE_LIMIT_SECONDS = _get_float_env("PHOTO_RATE_LIMIT_SECONDS", 15)
MIN_IMAGE_BYTES = _get_int_env("MIN_IMAGE_BYTES", 10240)
MAX_IMAGE_BYTES = _get_int_env("MAX_IMAGE_BYTES", 5242880)
