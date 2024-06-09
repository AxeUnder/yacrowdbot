from datetime import datetime, timedelta

import requests

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, MessageHandler, filters, ContextTypes,
                          ConversationHandler, CallbackQueryHandler)
from telegram.error import TelegramError
import pytz

from api import *


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.getLogger().setLevel(logging.INFO)

# A dictionary to keep track of the last post sent to each user
last_sent_posts = {}

# Define states for ConversationHandler
SET_TIME, SET_TIME_ZONE = range(2)


async def say_hi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Функция приветствия"""
    chat = update.effective_chat
    await context.bot.send_message(chat_id=chat.id, text='Привет, я CrowdBot!')


async def change_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Инициация смены времени рассылки"""
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

    logging.info(f'Текущие настройки времени: {start_time}-{end_time}')

    return SET_TIME


async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установка времени рассылки"""
    chat = update.effective_chat
    message = update.message.text
    logging.info(f"Получено сообщение от пользователя: {message}")
    keyboard = [
        [InlineKeyboardButton('Оставить текущие настройки', callback_data='keep_settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

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
                text='Неверный формат времени. Пожалуйста, используйте формат чч:мм-чч:мм.',
                reply_markup=reply_markup
            )
            return SET_TIME
    except ValueError:
        logging.error("Ошибка при разборе времени", exc_info=True)  # Добавлено для отслеживания ошибки
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

    logging.info(f'Текущий часовой пояс пользователя {chat.id}: {time_zone}')

    return SET_TIME_ZONE


async def set_time_zone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    message = update.message.text.strip()
    logging.info(f"Получено сообщение от пользователя {chat_id}: {message}")
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
        formatted_time_zone = f"{sign}{hours:02}:{minutes:02}"

        logging.info(f'Обновление часового пояса для пользователя {chat_id} на {formatted_time_zone}')

        updated_user = await update_user(chat_id, {'time_zone': formatted_time_zone})

        if updated_user and updated_user.get('time_zone') == formatted_time_zone:
            await context.bot.send_message(chat_id=chat_id, text=f'Ваш часовой пояс успешно установлен на {formatted_time_zone}!')
            logging.info(f'Часовой пояс {formatted_time_zone} успешно установлен для пользователя {chat_id}.')
            return ConversationHandler.END
        else:
            logging.error(f'Не удалось обновить часовой пояс для пользователя {chat_id}.')
            await context.bot.send_message(chat_id=chat_id, text='Не удалось обновить часовой пояс. Попробуйте снова позже.')
            return SET_TIME_ZONE

    except ValueError as error:
        await context.bot.send_message(
            chat_id=chat_id,
            text='Указанный вами часовой пояс не найден или имеет неверный формат. Пожалуйста, введите часовой пояс в формате ±чч:мм.',
            reply_markup=reply_markup
        )
        logging.error(f"Ошибка при установке часового пояса для пользователя {chat_id}: {error}")
        return SET_TIME_ZONE


async def wake_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск бота"""
    chat = update.effective_chat
    name = update.message.chat.username
    keyboard = [
        [InlineKeyboardButton('Помощь', callback_data='help')],
        [InlineKeyboardButton('Изменить время⌛', callback_data='change_time')],
        [InlineKeyboardButton('Изменить часовой пояс🌐', callback_data='change_time_zone')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Пробуем получить данные пользователя. Если он отсутствует, создадим нового пользователя.
    try:
        user = await get_user(chat.id)
        if not user:
            await store_user(chat.id, name)
        else:
            await update_user(chat.id, {'active': True})
    except Exception as e:
        logging.error(f'Ошибка при работе с таблицей Users: {e}')

    await context.bot.send_message(
        chat_id=chat.id,
        text=f'Спасибо, что включили меня, {name}!',
        reply_markup=reply_markup
    )


def convert_time_zone(time_zone):
    sign = time_zone[0]
    hours, minutes = map(int, time_zone[1:].split(':'))
    offset = hours * 60 + minutes
    if sign == '-':
        offset = -offset
    return pytz.FixedOffset(offset)


async def send_news(context: ContextTypes.DEFAULT_TYPE):
    """Рассылка новостей"""
    try:
        posts = await get_posts()
        now_utc = datetime.now(pytz.utc)

        users = await get_users()
        if not users:
            return

        for user in users:
            if user.get('active'):
                user_timezone_offset = user.get('time_zone')
                user_timezone = convert_time_zone(user_timezone_offset)

                now_local = now_utc.astimezone(user_timezone)
                start_time = datetime.strptime(user.get('start_time')[:5], '%H:%M').time()
                end_time = datetime.strptime(user.get('end_time')[:5], '%H:%M').time()

                logging.info(
                    f"Проверка времени для пользователя {user['id']}: now={now_local.time()}, start_time={start_time}, end_time={end_time}")

                if start_time <= now_local.time() <= end_time:
                    for post in posts:
                        if isinstance(post, dict) and 'date_create' in post and 'title' in post and 'text' in post:
                            try:
                                post_id = post['id']
                                if user['id'] in last_sent_posts and post_id <= last_sent_posts[user['id']]:
                                    continue  # Skip this post if it has already been sent to the user

                                post_time = datetime.strptime(post['date_create'], '%Y-%m-%dT%H:%M:%S.%fZ').replace(
                                    tzinfo=pytz.utc)
                                logging.info(f"Проверка времени поста: post_time={post_time}")

                                post_time_local = post_time.astimezone(user_timezone)

                                if post_time_local >= (now_local - timedelta(minutes=10)):
                                    post_content = f"{post['title']}\n\n{post['text']}"
                                    logging.info(f"Отправка сообщения пользователю {user['id']}: {post_content}")
                                    await context.bot.send_message(chat_id=user['id'], text=post_content)

                                    if post.get('image'):
                                        # Отправка всех изображений по одному
                                        for image_url in post['image']:
                                            try:
                                                response = requests.get(image_url)
                                                response.raise_for_status()  # Проверка на успешный статус код
                                                await context.bot.send_photo(chat_id=user['id'], photo=image_url)
                                            except requests.exceptions.RequestException as e:
                                                logging.error(f"Ошибка при получении изображения {image_url}: {e}")

                                    if post.get('video'):
                                        # Отправка всех видео по одному
                                        for video_url in post['video']:
                                            try:
                                                response = requests.get(video_url)
                                                response.raise_for_status()  # Проверка на успешный статус код
                                                await context.bot.send_video(chat_id=user['id'], video=video_url)
                                            except requests.exceptions.RequestException as e:
                                                logging.error(f"Ошибка при получении видео {video_url}: {e}")

                                    last_sent_posts[user['id']] = post_id  # Обновление ID последнего отправленного поста для пользователя

                            except Exception as e:
                                logging.error(f'Ошибка при отправке поста пользователю {user["id"]}: {e}')

    except Exception as e:
        logging.error(f'Ошибка при рассылке новостей: {e}')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Помощь по командам"""
    chat = update.effective_chat
    keyboard = [
        [InlineKeyboardButton('Помощь', callback_data='help')],
        [InlineKeyboardButton('Изменить время⌛', callback_data='change_time')],
        [InlineKeyboardButton('Изменить часовой пояс🌐', callback_data='change_time_zone')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
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
    keyboard = [
        [InlineKeyboardButton('Помощь', callback_data='help')],
        [InlineKeyboardButton('Изменить время⌛', callback_data='change_time')],
        [InlineKeyboardButton('Изменить часовой пояс🌐', callback_data='change_time_zone')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=chat.id,
        text='Текущие настройки оставлены без изменений.',
        reply_markup=reply_markup
    )

    return ConversationHandler.END


async def stop_sending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отключение рассылки новостей"""
    try:
        raise context.error
    except TelegramError as error:
        if 'blocked by the user' in str(error):
            chat_id = update.effective_chat.id
            await update_user(chat_id, {'active': False})
            logging.info(f'Пользователь {chat_id} заблокировал бота. Маркер активности был изменен в БД.')
        else:
            logging.error(f'Telegram error: {error}')


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
        logging.error(f'Ошибка при обработке нажатия кнопок: {e}')


def main():
    application = Application.builder().token(API_TOKEN).build()

    # Добавляем обработчик конверсации
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

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(r'\d+'), say_hi))

    application.add_error_handler(stop_sending)

    application.job_queue.run_repeating(send_news, interval=60, first=10)
    application.run_polling()


if __name__ == '__main__':
    main()
