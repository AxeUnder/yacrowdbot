import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, MessageHandler, filters, ContextTypes,
                          ConversationHandler, CallbackQueryHandler)
from telegram.error import TelegramError
import aiohttp
import logging
import pytz


load_dotenv()

API_TOKEN = os.getenv('API_TOKEN')
JETADMIN_API_KEY = os.getenv('JETADMIN_API_KEY')
API_URL_POST = os.getenv('API_URL_POST')
API_URL_USER = os.getenv('API_URL_USER')

HEADERS = {
    'Authorization': f'Bearer {JETADMIN_API_KEY}',
    'Content-Type': 'application/json'
}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Define states for ConversationHandler
SET_TIME = range(1)


async def get_posts():
    """Запрос на получение постов"""
    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL_POST, headers=HEADERS) as response:
            if response.status == 200:
                try:
                    data = await response.json()
                    logging.info(f"Полученные данные постов: {data}")
                    if 'results' in data and isinstance(data['results'], list):
                        return data['results']
                    else:
                        logging.error('Ответ API постов не содержит ключа results или не является списком')
                        return []
                except ValueError:
                    logging.error('Ошибка чтения ответа API постов')
                    return []
            else:
                logging.error(f'Ошибка получения постов: {response.status}')
                return []


async def get_users():
    """Запрос к таблице пользователей"""
    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL_USER, headers=HEADERS) as response:
            try:
                result = await response.json()
                users = result.get('results', [])
                logging.info(f'Получен ответ API пользователей: {result}')
                if not isinstance(users, list):
                    logging.error('Ответ API пользователей не является списком')
                    return []
                return users
            except ValueError as error:
                logging.error(f'Ошибка чтения ответа API пользователей: {error}')
                return []
            except Exception as e:
                logging.error(f'Неожиданная ошибка: {e}')
                return []


async def get_user(chat_id):
    """Запрос к данным пользователя"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{API_URL_USER}/{chat_id}', headers=HEADERS) as response:
            if response.status == 200:
                try:
                    user_data = await response.json()
                    return user_data
                except ValueError:
                    logging.error(f'Ошибка чтения данных пользователя: {response.status}')
                    return {}
            else:
                logging.error(f'Ошибка получения данных пользователя: {response.status}')
                return {}


async def store_user(chat_id, name):
    """Сохранение данных пользователя"""
    data = {
        'id': chat_id,
        'name': name
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL_USER, headers=HEADERS, json=data) as response:
            if response.status in (200, 201):
                try:
                    return await response.json()
                except ValueError:
                    logging.error('Ошибка чтения ответа API при сохранении пользователя')
                    return {}
            else:
                logging.error(f'Ошибка сохранения данных пользователя: {response.status}, ответ: {response.text}')
                return {}


async def update_user(chat_id, data):
    """Обновление данных пользователя"""
    async with aiohttp.ClientSession() as session:
        async with session.patch(f'{API_URL_USER}/{chat_id}', headers=HEADERS, json=data) as response:
            if response.status == 200:
                try:
                    return await response.json()
                except ValueError:
                    logging.error('Ошибка чтения ответа API при обновлении пользователя')
                    return {}
            else:
                logging.error(f'Ошибка обновления данных пользователя: {response.status}, ответ: {response.text}')
                return {}


async def say_hi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Функция приветствия"""
    chat = update.effective_chat
    await context.bot.send_message(chat_id=chat.id, text='Привет, я CrowdBot!')


async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установка времени"""
    chat = update.effective_chat
    message = update.message.text
    logging.info(f"Получено сообщение от пользователя: {message}")

    try:
        start_time, end_time = message.split('-')
        start_hour, start_minute = map(int, start_time.split(':'))
        end_hour, end_minute = map(int, end_time.split(':'))

        if 0 <= start_hour < 24 and 0 <= start_minute < 60 and 0 <= end_hour < 24 and 0 <= end_minute < 60:
            # Обновляем время в базе данных
            await update_user(chat.id, {
                'start_time': f'{start_hour:02}:{start_minute:02}',
                'end_time': f'{end_hour:02}:{end_minute:02}'
            })

            await context.bot.send_message(
                chat_id=chat.id,
                text=f'Время отправки новостей изменено на {start_hour:02}:{start_minute:02}-'
                     f'{end_hour:02}:{end_minute:02}'
            )
            logging.info(f"Время успешно изменено для пользователя {chat.id}")
            return ConversationHandler.END
        else:
            await context.bot.send_message(
                chat_id=chat.id,
                text='Неверный формат времени. Пожалуйста, используйте формат чч:мм-чч:мм.'
            )
            return SET_TIME
    except ValueError:
        logging.error("Ошибка при разборе времени", exc_info=True)  # Добавлено для отслеживания ошибки
        await context.bot.send_message(
            chat_id=chat.id,
            text='Неверный формат времени. Пожалуйста, используйте формат чч:мм-чч:мм.'
        )
        return SET_TIME


async def change_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Инициация смены времени"""
    chat = update.effective_chat
    response = await get_user(chat.id)

    start_time = response.get('start_time')
    end_time = response.get('end_time')

    # Преобразуем время из формата чч:мм:сс в чч:мм
    if len(start_time) > 5:
        start_time = start_time[:5]
    if len(end_time) > 5:
        end_time = end_time[:5]

    keyboard = [
        [InlineKeyboardButton('Оставить текущие настройки', callback_data='keep_settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=chat.id,
        text=f'Текущие настройки времени: {start_time}-{end_time}\n'
             'Для смены времени отправки новостей введите интервал времени в формате: чч:мм-чч:мм',
        reply_markup=reply_markup
    )
    return SET_TIME


async def keep_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Оставить текущие настройки времени"""
    chat = update.effective_chat

    await context.bot.send_message(chat_id=chat.id, text='Текущие настройки времени оставлены без изменений.')

    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Помощь по командам"""
    chat = update.effective_chat
    keyboard = [
        [InlineKeyboardButton('Помощь', callback_data='help')],
        [InlineKeyboardButton('Изменить время⌛', callback_data='change_time')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=chat.id,
        text='Команды бота:\n'
             '/start - запуск бота;\n'
             '/change_time - смена времени;\n'
             '/keep_settings - оставить текущие настройки;\n'
             '/help - помощь по командам.',
        reply_markup=reply_markup
    )


async def set_time_zone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установка часового пояса пользователя"""
    chat_id = update.effective_chat.id
    user_input = update.message.text.strip()

    try:
        # Проверяем, существует ли введенный пользователем часовой пояс
        pytz.timezone(user_input)

        # Обновляем данные пользователя в базе данных
        await update_user(chat_id, {'time_zone': user_input})

        await update.message.reply_text("Ваш часовой пояс успешно установлен!")

        # Устанавливаем активность пользователя после установки часового пояса
        await update_user(chat_id, {'active': True})
    except pytz.exceptions.UnknownTimeZoneError:
        await update.message.reply_text(
            "Указанный вами часовой пояс не найден. Пожалуйста, введите часовой пояс в формате '+HH:MM'.")

    return ConversationHandler.END


async def wake_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск бота"""
    chat = update.effective_chat
    name = update.message.chat.username
    keyboard = [
        [InlineKeyboardButton('Помощь', callback_data='help')],
        [InlineKeyboardButton('Изменить время⌛', callback_data='change_time')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Пробуем получить данные пользователя. Если он отсутствует, создадим нового пользователя.
    try:
        user = await get_user(chat.id)
        if not user:
            await store_user(chat.id, name)
            # Запрашиваем и сохраняем часовой пояс пользователя
            await context.bot.send_message(
                chat_id=chat.id,
                text="Пожалуйста, укажите ваш текущий часовой пояс в формате '±HH:MM'. Например, '+03:00' для Москвы."
            )
            # Устанавливаем состояние ожидания ответа о часовом поясе пользователя
            context.user_data['state'] = 'time_zone'
            return SET_TIME
        else:
            await update_user(chat.id, {'active': True})
    except Exception as e:
        logging.error(f'Ошибка при работе с таблицей Users: {e}')

    await context.bot.send_message(
        chat_id=chat.id,
        text=f'Спасибо, что включили меня, {name}!',
        reply_markup=reply_markup
    )


async def send_news(context: ContextTypes.DEFAULT_TYPE):
    """Рассылка новостей"""
    try:
        posts = await get_posts()
        now = datetime.now()

        users = await get_users()
        if not users:
            return

        for user in users:
            if user.get('active'):
                # Получаем часовой пояс пользователя
                user_timezone_name = user.get('time_zone')
                # Преобразуем часовой пояс пользователя из формата '+03:00' в стандартное имя часового пояса
                user_timezone_name_standard = pytz.country_timezones['RU'][0]

                try:
                    # Создаем объект pytz.timezone
                    user_timezone = pytz.timezone(user_timezone_name_standard)

                    now_local = now.astimezone(user_timezone)

                    start_time = datetime.strptime(user.get('start_time'), '%H:%M').time()
                    end_time = datetime.strptime(user.get('end_time'), '%H:%M').time()

                    logging.info(f"Проверка времени для пользователя {user['id']}: now={now_local.time()}, start_time={start_time}, end_time={end_time}")

                    if start_time <= now_local.time() <= end_time:
                        for post in posts:
                            if isinstance(post, dict) and 'date_create' in post and 'title' in post and 'text' in post:
                                try:
                                    # Преобразуем время поста в локальное время пользователя
                                    post_time = datetime.strptime(post['date_create'], '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=pytz.utc).astimezone(user_timezone).time()
                                    logging.info(f"Проверка времени поста: post_time={post_time}")

                                    if post_time >= (now_local - timedelta(minutes=10)).time():
                                        post_content = f"{post['title']}\n\n{post['text']}"
                                        logging.info(f"Отправка сообщения пользователю {user['id']}: {post_content}")
                                        await context.bot.send_message(chat_id=user['id'], text=post_content)

                                        if post.get('image'):
                                            for image in post['image']:
                                                await context.bot.send_photo(chat_id=user['id'], photo=image)

                                        if post.get('video'):
                                            for video in post['video']:
                                                await context.bot.send_video(chat_id=user['id'], video=video)
                                except TelegramError as error:
                                    logging.error(f'Ошибка при отправке поста: {error}')
                            else:
                                logging.error('Некорректная структура данных поста')
                except pytz.exceptions.UnknownTimeZoneError:
                    logging.error(f'Не удалось создать объект pytz.timezone для пользователя {user["id"]}. Неизвестный часовой пояс: {user_timezone_name_standard}')
                except KeyError:
                    logging.error(f"Не удалось найти стандартное имя часового пояса для пользователя {user['id']}")
    except Exception as e:
        logging.error(f'Ошибка при отправке новостей: {e}', exc_info=True)


async def button_click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия кнопок"""
    query = update.callback_query
    query_data = query.data

    if query_data == 'help':
        await help_command(update, context)
    elif query_data == 'change_time':
        await change_time(update, context)
    elif query_data == 'keep_settings':
        await keep_settings(update, context)


async def handle_telegram_error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ошибок Telegram"""
    try:
        raise context.error
    except TelegramError as error:
        if 'blocked by the user' in str(error):
            chat_id = update.effective_chat.id
            await update_user(chat_id, {'active': False})
            logging.info(f'Пользователь {chat_id} заблокировал бота. Маркер активности был изменен в БД.')
        else:
            logging.error(f'Telegram error: {error}')


def main():
    application = Application.builder().token(API_TOKEN).build()

    # ConversationHandler для смены времени
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(change_time, pattern='^change_time$')],
        states={
            SET_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_time)]
        },
        fallbacks=[CallbackQueryHandler(keep_settings, pattern='^keep_settings$')],
        per_message=False
    )

    # Обработчики команд
    application.add_handler(CommandHandler('start', wake_up))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('change_time', change_time))
    application.add_handler(CommandHandler('keep_settings', keep_settings))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_click_handler))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, say_hi))

    application.add_error_handler(handle_telegram_error)

    application.job_queue.run_repeating(send_news, interval=60, first=10)

    application.run_polling()


if __name__ == '__main__':
    main()
