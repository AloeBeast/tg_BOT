import base64
import logging

from config import AI_API_KEY, AI_BASE_URL, AI_MODEL_VISION
from openai import OpenAI

logger = logging.getLogger(__name__)
vision_client = OpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)


def describe_image(image_bytes: bytes) -> str:
    """Отправляет фото в Llama Vision и возвращает подробное текстовое описание."""
    try:
        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        response = vision_client.chat.completions.create(
            model=AI_MODEL_VISION,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Подробно опиши, что изображено на этом фото. "
                                    "Упомяни объекты, людей (без попыток узнать личность), "
                                    "обстановку, текст на фото если есть, общее настроение фото."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=300,
        )
        return response.choices[0].message.content or "Не удалось распознать изображение."
    except Exception:
        logger.exception("AI vision request failed")
        return "Не удалось проанализировать фото, попробуйте позже."
