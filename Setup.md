# Setup сервера для tg_BOT

Инструкция рассчитана на Ubuntu/Debian-сервер и запуск Telegram-бота через `systemd`.

## 1. Подготовка сервера

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
```

## 2. Загрузка проекта

```bash
cd /opt
sudo git clone <URL_РЕПОЗИТОРИЯ> tg_BOT
sudo chown -R "$USER":"$USER" /opt/tg_BOT
cd /opt/tg_BOT
```

Если проект уже загружен, просто перейдите в его папку:

```bash
cd /opt/tg_BOT
```

## 3. Виртуальное окружение и зависимости

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Переменные окружения

Создайте файл `.env` на основе примера:

```bash
cp .env.example .env
nano .env
```

Минимально нужно заполнить:

```env
BOT_TOKEN=telegram_bot_token
AI_API_KEY=api_key_for_openai_compatible_provider
AI_BASE_URL=https://api.example.com/v1
AI_MODEL=glm-5v-turbo
```

Дополнительные настройки:

```env
DEBUG_MODE=false
HISTORY_LIMIT=8
AI_CHAT_TIMEOUT_SECONDS=30
AI_RETRY_COUNT=1
PHOTO_RATE_LIMIT_SECONDS=15
MIN_IMAGE_BYTES=10240
MAX_IMAGE_BYTES=5242880
```

## 5. Проверка запуска вручную

```bash
source venv/bin/activate
python main.py
```

Если бот стартовал без ошибок, остановите его через `Ctrl+C` и настройте сервис.

## 6. Systemd-сервис

Создайте файл сервиса:

```bash
sudo nano /etc/systemd/system/tg-bot.service
```

Вставьте конфигурацию, заменив `User` и пути при необходимости:

```ini
[Unit]
Description=tg_BOT Telegram bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/tg_BOT
EnvironmentFile=/opt/tg_BOT/.env
ExecStart=/opt/tg_BOT/venv/bin/python /opt/tg_BOT/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Активируйте сервис:

```bash
sudo systemctl daemon-reload
sudo systemctl enable tg-bot
sudo systemctl start tg-bot
```

## 7. Логи и управление

Проверить статус:

```bash
sudo systemctl status tg-bot
```

Смотреть логи:

```bash
sudo journalctl -u tg-bot -f
```

Перезапустить после обновления кода или `.env`:

```bash
sudo systemctl restart tg-bot
```

Остановить:

```bash
sudo systemctl stop tg-bot
```

## 8. Обновление проекта на сервере

```bash
cd /opt/tg_BOT
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart tg-bot
```

## 9. Частые ошибки

- `ValueError: Не найдена переменная окружения ...` — проверьте `.env` и `EnvironmentFile` в systemd.
- Бот не отвечает — проверьте `BOT_TOKEN`, доступ сервера к интернету и логи `journalctl`.
- Ошибка AI API — проверьте `AI_API_KEY`, `AI_BASE_URL`, `AI_MODEL` и совместимость провайдера с OpenAI Chat Completions API.
- Фото не обрабатываются — проверьте лимиты `MIN_IMAGE_BYTES`, `MAX_IMAGE_BYTES` и поддержку multimodal-запросов выбранной моделью.
