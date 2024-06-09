import aiohttp
import logging
from config import *


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
    logging.info(f'Отправка данных для обновления пользователя {chat_id}: {data}')
    async with aiohttp.ClientSession() as session:
        try:
            async with session.patch(f'{API_URL_USER}/{chat_id}', headers=HEADERS, json=data) as response:
                response_text = await response.text()
                logging.info(f'Ответ от API при обновлении данных пользователя {chat_id}: {response_text}')
                if response.status == 200:
                    try:
                        updated_data = await response.json()
                        logging.info(f'Данные пользователя обновлены: {updated_data}')
                        return updated_data
                    except ValueError as e:
                        logging.error(f'Ошибка чтения ответа API при обновлении пользователя: {e}')
                        return {}
                else:
                    logging.error(f'Ошибка обновления данных пользователя: {response.status}, ответ: {response_text}')
                    return {}
        except Exception as e:
            logging.error(f'Неожиданная ошибка при обновлении данных пользователя: {e}')
            return {}