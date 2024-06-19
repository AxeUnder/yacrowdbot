# Рекламный чат-бот yacrowdbot

## Описание
Yacrowdbot чат-бот предполагает автоматизацию рутинных процессов, что позволяет сократить время и ресурсы, затрачиваемые на выполнение этих задач. Это включает в себя оперативную рассылку новостей, повышение оперативности реагирования и совершенствование взаимодействия с клиентами.

**Инструменты и стек:** #Python3.9 #python-telegram-bot #HTTPX #requests #asyncio #pytz #logging #dotenv #PyCharm (для разработки)

## Установка
1. Клонируйте репозиторий:
    ```sh
    git clone https://github.com/axeunder/yacrowdbot.git
    cd yacrowdbot
    ```
2. Установите зависимости:
    ```sh
    pip install -r requirements.txt
    ```
3. Настройте переменные окружения. Создайте файл `.env` и добавьте ваш токен Telegram API, а также URL API и другие необходимые переменные:
    ```sh
    API_TOKEN=ваш_токен_telegram_api
    JETADMIN_API_KEY=ваш_токен_jet_aadmin_api
    API_URL_POST=ваш_url_для_api_потов
    API_URL_USER=ваш_url_для_api_пользователей
    ```
4. Запустите бота:
    ```sh
    python yacrowdbot.py
    ```

## Использование
После запуска бот начнет опрос Telegram API и будет готов обрабатывать команды и текстовые сообщения от пользователей. 

### Основные команды
- `/start` - запуск бота и приветствие пользователя.
- `/help` - получение списка доступных команд.
- `/change_time` - смена времени рассылки новостей.
- `/change_time_zone` - смена часового пояса.
- `/keep_settings` - оставить текущие настройки без изменений.

## Функциональность
### Приветствие
Бот приветствует пользователя при запуске с помощью команды `/start`. 

### Смена времени рассылки
Пользователь может сменить время рассылки новостей с помощью команды `/change_time`. Время вводится в формате `чч:мм-чч:мм`.

### Смена часового пояса
С помощью команды `/change_time_zone` пользователь может сменить часовой пояс. Ввод осуществляется в формате `±чч:мм`.

### Обработка текстовых сообщений
Бот также отвечает на текстовые сообщения, отправляя стандартное приветственное сообщение.

### Рассылка новостей
Бот автоматически отправляет новости пользователям в заданные интервалы времени. Новости включают текст, изображения и видео.

### Обработка ошибок
Бот обрабатывает ошибки, возникающие при отправке сообщений, включая блокировку пользователя.

## Пример кода

```python
import asyncio
from datetime import datetime, timedelta
import logging
import requests
import pytz
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, CallbackQueryHandler
)
from telegram.error import TelegramError
from telegram.request import HTTPXRequest

from api import get_user, update_user, store_user, get_posts, get_users
from config import API_TOKEN

# Настройка логирования
logging.basicConfig(format='%(asctime)s-%(name)s-%(levelname)s-%(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Словарь для отслеживания последнего отправленного поста для каждого пользователя
last_sent_posts = {}

# Определение состояний для ConversationHandler
SET_TIME, SET_TIME_ZONE = range(2)

# Настройка тайм-аутов и лимитов для HTTPXRequest
request = HTTPXRequest(
    connect_timeout=10.0,
    read_timeout=300.0,
    write_timeout=300.0,
    pool_timeout=5.0
)

DEFAULT_KEYBOARD = [
    [InlineKeyboardButton('Помощь', callback_data='help')],
    [InlineKeyboardButton('Изменить время⌛', callback_data='change_time')],
    [InlineKeyboardButton('Изменить часовой пояс🌐', callback_data='change_time_zone')]
]

KEYBOARD_CANCEL = [
    [InlineKeyboardButton('Оставить текущие настройки', callback_data='keep_settings')]
]

async def say_hi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Функция приветствия"""
    chat = update.effective_chat
    reply_markup = InlineKeyboardMarkup(DEFAULT_KEYBOARD)
    try:
        await context.bot.send_message(
            chat_id=chat.id,
            text='Привет, я CrowdBot!',
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f'Ошибка при отправке приветственного сообщения пользователю {chat.id}: {e}')
```

# Об авторе
Python-разработчик
> [AxeUnder](https://github.com/AxeUnder).
