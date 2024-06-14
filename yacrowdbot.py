from datetime import datetime, timedelta

import requests

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, MessageHandler, filters, ContextTypes,
                          ConversationHandler, CallbackQueryHandler)
from telegram.error import TelegramError
import pytz
from telegram.request import HTTPXRequest

from api import *

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Словарь для отслеживания последнего отправленного поста для каждого пользователя
last_sent_posts = {}

# Определение состояний для ConversationHandler
SET_TIME, SET_TIME_ZONE = range(2)

# Настройка тайм-аутов и лимитов для HTTPXRequest
request = HTTPXRequest(
    connect_timeout=50.0,
    read_timeout=200.0,
    write_timeout=200.0,
    pool_timeout=300.0
)

DEFAULT_KEYBOARD = [
    [InlineKeyboardButton('Помощь', callback_data='help')],
    [InlineKeyboardButton('Изменить время⌛', callback_data='change_time')],
    [InlineKeyboardButton('Изменить часовой пояс🌐', callback_data='change_time_zone')]
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


async def change_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Инициация смены времени рассылки"""
    chat = update.effective_chat
    response = await get_user(chat.id)

    start_time = response.get('start_time')
    end_time = response.get('end_time')

    # Преобразование времени из формата чч:мм:сс в чч:мм
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
    logger.info(f'Пользователь {chat.id} запросил смену времени. Текущие настройки: {start_time}-{end_time}')
    return SET_TIME


async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установка времени рассылки"""
    chat = update.effective_chat
    message = update.message.text
    logger.info(f'Получено сообщение от пользователя {chat.id}: {message}')
    keyboard = [
        [InlineKeyboardButton('Оставить текущие настройки', callback_data='keep_settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        start_time, end_time = message.split('-')
        start_hour, start_minute = map(int, start_time.split(':'))
        end_hour, end_minute = map(int, end_time.split(':'))

        if 0 <= start_hour < 24 and 0 <= start_minute < 60 and 0 <= end_hour < 24 and 0 <= end_minute < 60:
            await update_user(chat.id, {
                'start_time': f'{start_hour:02}:{start_minute:02}',
                'end_time': f'{end_hour:02}:{end_minute:02}'
            })

            await context.bot.send_message(
                chat_id=chat.id,
                text=f'Время отправки новостей изменено на {start_hour:02}:{start_minute:02}-'
                     f'{end_hour:02}:{end_minute:02}'
            )
            logger.info(f'Время успешно изменено для пользователя {chat.id} на {start_hour:02}:{start_minute:02}-{end_hour:02}:{end_minute:02}')
            return ConversationHandler.END
        else:
            await context.bot.send_message(
                chat_id=chat.id,
                text='Неверный формат времени. Пожалуйста, используйте формат чч:мм-чч:мм.',
                reply_markup=reply_markup
            )
            return SET_TIME
    except ValueError:
        logger.error(f'Неверный формат времени от пользователя {chat.id}: {message}', exc_info=True)
        await context.bot.send_message(
            chat_id=chat.id,
            text='Неверный формат времени. Пожалуйста, используйте формат чч:мм-чч:мм.',
            reply_markup=reply_markup
        )
        return SET_TIME


async def change_time_zone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Инициализация смены часового пояса"""
    chat = update.effective_chat
    response = await get_user(chat.id)

    time_zone = response.get('time_zone')

    keyboard = [
        [InlineKeyboardButton('Оставить текущие настройки', callback_data='keep_settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=chat.id,
        text=f'Ваш текущий часовой пояс: {time_zone}\n'
             'Для смены часового пояса введите его в формате ±чч:мм:',
        reply_markup=reply_markup
    )

    logger.info(f'Пользователь {chat.id} запросил смену часового пояса. Текущие настройки: {time_zone}')
    return SET_TIME_ZONE


async def set_time_zone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    message = update.message.text.strip()
    logger.info(f'Получено сообщение от пользователя {chat_id}: {message}')
    keyboard = [
        [InlineKeyboardButton('Оставить текущие настройки', callback_data='keep_settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if not (message.startswith('+') or message.startswith('-')) or ':' not in message:
            raise ValueError('Неверный формат часового пояса')

        hours_minutes = message[1:].split(':')
        if len(hours_minutes) != 2:
            raise ValueError('Неверный формат часового пояса')

        hours, minutes = map(int, hours_minutes)

        if not (0 <= hours < 24 and 0 <= minutes < 60):
            raise ValueError('Неверное значение часов или минут')

        sign = message[0]
        formatted_time_zone = f'{sign}{hours:02}:{minutes:02}'

        logger.info(f'Обновление часового пояса для пользователя {chat_id} на {formatted_time_zone}')

        updated_user = await update_user(chat_id, {'time_zone': formatted_time_zone})

        if updated_user and updated_user.get('time_zone') == formatted_time_zone:
            await context.bot.send_message(chat_id=chat_id, text=f'Ваш часовой пояс успешно установлен на {formatted_time_zone}!')
            logger.info(f'Часовой пояс {formatted_time_zone} успешно установлен для пользователя {chat_id}.')
            return ConversationHandler.END
        else:
            logger.error(f'Не удалось обновить часовой пояс для пользователя {chat_id}.')
            await context.bot.send_message(chat_id=chat_id, text='Не удалось обновить часовой пояс. Попробуйте снова позже.')
            return SET_TIME_ZONE

    except ValueError as error:
        await context.bot.send_message(
            chat_id=chat_id,
            text='Указанный вами часовой пояс не найден или имеет неверный формат. Пожалуйста, введите часовой пояс в формате ±чч:мм.',
            reply_markup=reply_markup
        )
        logger.error(f"Ошибка при установке часового пояса для пользователя {chat_id}: {error}")
        return SET_TIME_ZONE


async def wake_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск бота"""
    chat = update.effective_chat
    name = update.message.chat.username
    reply_markup = InlineKeyboardMarkup(DEFAULT_KEYBOARD)

    try:
        user = await get_user(chat.id)
        if not user:
            await store_user(chat.id, name)
            logger.info(f'Новый пользователь {chat.id} ({name}) добавлен в базу данных.')
        else:
            await update_user(chat.id, {'active': True})
            logger.info(f'Пользователь {chat.id} ({name}) активировал бота.')
    except Exception as e:
        logger.error(f'Ошибка при работе с таблицей Users для пользователя {chat.id} ({name}): {e}')

    await context.bot.send_message(
        chat_id=chat.id,
        text=f'Спасибо, что включили меня, {name}!',
        reply_markup=reply_markup
    )
    logger.debug(f'Отправлено сообщение о включении бота пользователю {chat.id}')


def convert_time_zone(time_zone):
    sign = time_zone[0]
    hours, minutes = map(int, time_zone[1:].split(':'))
    offset = hours * 60 + minutes
    if sign == '-':
        offset = -offset
    return pytz.FixedOffset(offset)


async def handle_block_error(chat_id):
    """Обработка ошибки блокировки бота пользователем"""
    try:
        await update_user(chat_id, {'active': False})
        logging.info(f'Пользователь {chat_id} заблокировал бота. Маркер активности был изменен в БД.')
    except Exception as e:
        logging.error(f'Ошибка при обновлении статуса пользователя {chat_id} в БД: {e}')


async def send_news(context: ContextTypes.DEFAULT_TYPE):
    """Рассылка новостей"""
    try:
        posts = await get_posts()
        now_utc = datetime.now(pytz.utc)

        users = await get_users()
        if not users:
            logger.info('Нет активных пользователей для рассылки новостей.')
            return

        # Временное хранилище для загруженных видео
        video_cache = {}

        for user in users:
            if user.get('active'):
                user_timezone_offset = user.get('time_zone')
                user_timezone = convert_time_zone(user_timezone_offset)

                now_local = now_utc.astimezone(user_timezone)
                start_time = datetime.strptime(user.get('start_time')[:5], '%H:%M').time()
                end_time = datetime.strptime(user.get('end_time')[:5], '%H:%M').time()

                logger.info(f"Проверка времени для пользователя {user['id']}: now={now_local.time()}, start_time={start_time}, end_time={end_time}")

                # Проверка временного интервала с учетом пересечения дня
                if (start_time <= end_time and start_time <= now_local.time() <= end_time) or \
                        (start_time > end_time and (now_local.time() >= start_time or now_local.time() <= end_time)):
                    for post in posts:
                        if isinstance(post, dict) and 'date_create' in post and 'title' in post and 'text' in post:
                            try:
                                post_id = post['id']
                                if user['id'] in last_sent_posts and post_id <= last_sent_posts[user['id']]:
                                    continue  # Skip this post if it has already been sent to the user

                                post_time = datetime.strptime(post['date_create'], '%Y-%m-%dT%H:%M:%S.%fZ').replace(
                                    tzinfo=pytz.utc)
                                logger.info(f'Проверка времени поста: post_time={post_time}')

                                post_time_local = post_time.astimezone(user_timezone)

                                if post_time_local >= (now_local - timedelta(minutes=10)):
                                    post_content = f"{post['title']}\n\n{post['text']}"
                                    logger.info(f"Отправка сообщения пользователю {user['id']}: {post_content}")
                                    await context.bot.send_message(chat_id=user['id'], text=post_content)

                                    if post.get('image'):
                                        for image_url in post['image']:
                                            try:
                                                response = requests.get(image_url)
                                                response.raise_for_status()  # Проверка на успешный статус код
                                                await context.bot.send_photo(chat_id=user['id'], photo=image_url)
                                                logger.info(f"Изображение успешно отправлено пользователю {user['id']}")
                                            except requests.exceptions.RequestException as e:
                                                logger.error(f'Ошибка при получении изображения {image_url}: {e}')

                                    if post.get('video'):
                                        for video_url in post['video']:
                                            try:
                                                # Проверка, было ли видео уже загружено
                                                if video_url in video_cache:
                                                    video_path = video_cache[video_url]
                                                else:
                                                    response = requests.get(video_url)
                                                    response.raise_for_status()
                                                    # Загрузка видео
                                                    video_data = response.content
                                                    video_path = f'/mnt/data/{os.path.basename(video_url)}'
                                                    # Убедимся, что директория существует
                                                    os.makedirs(os.path.dirname(video_path), exist_ok=True)

                                                    with open(video_path, 'wb') as video_file:
                                                        video_file.write(video_data)
                                                    # Сохранение пути к видео в кэш
                                                    video_cache[video_url] = video_path
                                                # Отправка видео
                                                with open(video_path, 'rb') as video_file:
                                                    await context.bot.send_video(chat_id=user['id'], video=video_file)
                                                logger.info(f"Видео успешно отправлено пользователю {user['id']}")

                                            except requests.exceptions.RequestException as e:
                                                logger.error(f'Ошибка при получении видео {video_url}: {e}')
                                            except TelegramError as error:
                                                logger.error(f'Ошибка Telegram при отправке видео {video_url}: {error}')

                                    # Удаление старых записей из списка отправленных постов
                                    if len(last_sent_posts[user['id']]) > 10:
                                        last_sent_posts[user['id']].pop(0)
                                    # Обновление ID последнего отправленного поста для пользователя
                                    last_sent_posts[user['id']] = post_id

                            except TelegramError as error:
                                if 'blocked by the user' in str(error):
                                    await handle_block_error(user['id'])
                                else:
                                    logger.error(f"Ошибка при отправке поста пользователю {user['id']}: {error}")

        # Удаление временных файлов после рассылки всем пользователям
        for video_path in video_cache.values():
            try:
                os.remove(video_path)
                logger.info(f'Временный файл {video_path} удален.')
            except OSError as error:
                logger.error(f'Ошибка при удалении временного файла {video_path}: {error}')

    except Exception as e:
        logger.error(f'Ошибка при рассылке новостей: {e}')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Помощь по командам"""
    chat = update.effective_chat
    reply_markup = InlineKeyboardMarkup(DEFAULT_KEYBOARD)
    await context.bot.send_message(
        chat_id=chat.id,
        text='Команды бота:\n'
             '/start - запуск бота;\n'
             '/change_time - смена времени;\n'
             '/change_time_zone - смена часового пояса;\n'
             '/keep_settings - оставить текущие настройки;\n'
             '/help - помощь по командам.',
        reply_markup=reply_markup
    )


async def keep_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Оставить текущие настройки"""
    chat = update.effective_chat
    reply_markup = InlineKeyboardMarkup(DEFAULT_KEYBOARD)
    await context.bot.send_message(
        chat_id=chat.id,
        text='Текущие настройки оставлены без изменений.',
        reply_markup=reply_markup
    )

    return ConversationHandler.END


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатия кнопок"""
    try:
        query = update.callback_query
        query_data = query.data
        await query.answer()

        if query_data == 'help':
            await help_command(update, context)
            return
        elif query_data == 'change_time':
            await change_time(update, context)
            return SET_TIME
        elif query_data == 'change_time_zone':
            await change_time_zone(update, context)
            return SET_TIME_ZONE
        elif query_data == 'keep_settings':
            await keep_settings(update, context)
            return ConversationHandler.END
    except Exception as e:
        logger.error(f'Ошибка при обработке нажатия кнопок: {e}')


def main():
    application = Application.builder().token(API_TOKEN).request(request).build()

    # Обработчик конверсии
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', wake_up),
            CommandHandler('help', help_command),
            CommandHandler('change_time', change_time),
            CommandHandler('change_time_zone', change_time_zone),
            CallbackQueryHandler(button_handler)
        ],
        states={
            SET_TIME: [
                CallbackQueryHandler(button_handler, pattern='^keep_settings$'),
                CommandHandler('keep_settings', keep_settings),
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_time)
            ],
            SET_TIME_ZONE: [
                CallbackQueryHandler(button_handler, pattern='^keep_settings$'),
                CommandHandler('keep_settings', keep_settings),
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_time_zone)
            ],
        },
        fallbacks=[
            CallbackQueryHandler(button_handler, pattern='^keep_settings$'),
            CommandHandler('keep_settings', keep_settings),
            MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler)
        ],
        per_message=False
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler))

    application.add_handler(CommandHandler('start', wake_up))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('keep_settings', keep_settings))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, say_hi))

    application.job_queue.run_repeating(send_news, interval=600, first=10)
    application.run_polling()


if __name__ == '__main__':
    main()
