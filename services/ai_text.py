import json
import logging

from openai import OpenAI

from persona import PERSONA_PROMPT

from config import AI_API_KEY, AI_BASE_URL, AI_MODEL, AI_MODEL_FAST, AI_CHAT_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)
ai_client = OpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)


def get_ai_reply(messages: list[dict[str, str]]) -> str:
    """Отправляет историю сообщений нейросети и возвращает текстовый ответ."""
    response = ai_client.chat.completions.create(
        model=AI_MODEL,
        messages=messages,  # type: ignore[arg-type]
        max_tokens=250,  # жёсткий потолок длины ответа — экономит токены
        timeout=AI_CHAT_TIMEOUT_SECONDS,
    )
    return response.choices[0].message.content or "Не удалось получить ответ."


def extract_profile_update(user_text: str) -> dict[str, str]:
    """Проверяет сообщение на наличие имени/фактов о пользователе."""
    try:
        response = ai_client.chat.completions.create(
            model=AI_MODEL_FAST,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты — модуль извлечения фактов. Проанализируй сообщение пользователя. "
                        "Если пользователь сообщает своё имя — верни его в поле name. "
                        "Если в сообщении есть важный факт о пользователе (предпочтения, работа, "
                        "интересы, обстоятельства) — кратко сформулируй его в поле fact (одно предложение). "
                        "Если ничего важного нет — оставь поля пустыми. "
                        "Ответь СТРОГО в формате JSON без каких-либо пояснений: "
                        '{"name": "", "fact": ""}'
                    ),
                },
                {"role": "user", "content": user_text},
            ],
            max_tokens=100,
            timeout=AI_CHAT_TIMEOUT_SECONDS,
        )
        raw = response.choices[0].message.content or "{}"
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        return {
            "name": data.get("name", "") or "",
            "fact": data.get("fact", "") or "",
        }
    except Exception:
        logger.exception("Profile extraction failed")
        return {"name": "", "fact": ""}


def build_system_prompt(profile: dict[str, str]) -> str:
    """Собирает системную инструкцию для нейросети: персонаж + профиль пользователя."""
    base = PERSONA_PROMPT

    if profile["name"]:
        base += f"\n\nПользователя зовут {profile['name']}."

    if profile["facts"]:
        base += f"\nИзвестные факты о пользователе:{profile['facts']}"

    return base
