import base64
import hashlib
import logging
from collections import OrderedDict

from config import (
    AI_API_KEY,
    AI_BASE_URL,
    AI_MODEL_VISION,
    AI_VISION_TIMEOUT_SECONDS,
    VISION_CACHE_MAX_ITEMS,
)
from openai import OpenAI

logger = logging.getLogger(__name__)
vision_client = OpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)
_vision_cache: OrderedDict[str, str] = OrderedDict()


def describe_image(image_bytes: bytes) -> str:
    """Отправляет фото в Llama Vision и возвращает подробное текстовое описание."""
    image_hash = hashlib.sha256(image_bytes).hexdigest()
    cached_description = _vision_cache.get(image_hash)
    if cached_description is not None:
        _vision_cache.move_to_end(image_hash)
        logger.debug("Vision cache hit: %s", image_hash)
        return cached_description

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
        timeout=AI_VISION_TIMEOUT_SECONDS,
    )
    description = response.choices[0].message.content or "Не удалось распознать изображение."
    _vision_cache[image_hash] = description
    if len(_vision_cache) > VISION_CACHE_MAX_ITEMS:
        _vision_cache.popitem(last=False)
    return description
