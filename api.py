import aiohttp
import logging
from config import API_URL_POST, API_URL_USER, HEADERS

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def get_posts():
    """Запрос на получение постов"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(API_URL_POST, headers=HEADERS) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                        logger.info(f'Полученные данные постов: {data}')
                        if 'results' in data \
                                and isinstance(data['results'], list):
                            return data['results']
                        else:
                            logger.error(
                                'Ответ API постов не содержит ключа results '
                                'или не является списком'
                            )
                            return []
                    except ValueError as error:
                        logger.error(
                            'Ошибка чтения ответа API постов: '
                            f'{error}'
                        )
                        return []
                else:
                    logger.error(f'Ошибка получения постов: {response.status}')
                    return []
        except aiohttp.ClientError as error:
            logger.error(f'Ошибка сети при получении постов: {error}')
            return []


async def get_users():
    """Запрос к таблице пользователей"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(API_URL_USER, headers=HEADERS) as response:
                try:
                    result = await response.json()
                    users = result.get('results', [])
                    logger.info(f'Получен ответ API пользователей: {result}')
                    if not isinstance(users, list):
                        logging.error(
                            'Ответ API пользователей не является списком'
                        )
                        return []
                    return users
                except ValueError as error:
                    logger.error(
                        f'Ошибка чтения ответа API пользователей: {error}'
                    )
                    return []
                except Exception as e:
                    logging.error(f'Неожиданная ошибка: {e}')
                    return []
        except aiohttp.ClientError as error:
            logger.error(f'Ошибка сети при получении пользователей: {error}')
            return []


async def get_user(chat_id):
    """Запрос к данным пользователя"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                f'{API_URL_USER}/{chat_id}', headers=HEADERS
            ) as response:
                if response.status == 200:
                    try:
                        user_data = await response.json()
                        return user_data
                    except ValueError as error:
                        logger.error(
                            f'Ошибка чтения данных пользователя: {error}'
                        )
                        return {}
                else:
                    logger.error(
                        'Ошибка получения данных пользователя: '
                        f'{response.status}'
                    )
                    return {}
        except aiohttp.ClientError as error:
            logger.error(
                f'Ошибка сети при получении данных пользователя: {error}'
            )
            return {}


async def store_user(chat_id, name):
    """Сохранение данных пользователя"""
    data = {
        'id': chat_id,
        'name': name
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                API_URL_USER, headers=HEADERS, json=data
            ) as response:
                if response.status in (200, 201):
                    try:
                        return await response.json()
                    except ValueError as error:
                        logger.error(
                            'Ошибка чтения ответа API при сохранении '
                            f'пользователя: {error}'
                        )
                        return {}
                else:
                    response_text = await response.text()
                    logger.error(
                        'Ошибка сохранения данных пользователя: '
                        f'{response.status}, ответ: {response_text}'
                    )
                    return {}
        except aiohttp.ClientError as error:
            logger.error(
                f'Ошибка сети при сохранении данных пользователя: {error}'
            )
            return {}


async def update_user(chat_id, data):
    """Обновление данных пользователя"""
    logging.info(
        f'Отправка в БД данных пользователя {chat_id}: {data}'
    )
    async with aiohttp.ClientSession() as session:
        try:
            async with session.patch(
                f'{API_URL_USER}/{chat_id}', headers=HEADERS, json=data
            ) as response:
                response_text = await response.text()
                logger.info(
                    'Ответ от API при обновлении данных пользователя '
                    f'{chat_id}: {response_text}'
                )
                if response.status == 200:
                    try:
                        updated_data = await response.json()
                        logger.info(
                            f'Данные пользователя обновлены: {updated_data}'
                        )
                        return updated_data
                    except ValueError as error:
                        logger.error(
                            'Ошибка чтения ответа API при обновлении '
                            f'пользователя: {error}'
                        )
                        return {}
                else:
                    logger.error(
                        'Ошибка обновления данных пользователя: '
                        f'{response.status}, ответ: {response_text}'
                    )
                    return {}
        except aiohttp.ClientError as error:
            logger.error(
                f'Ошибка сети при обновлении данных пользователя: {error}'
            )
            return {}
        except Exception as error:
            logger.error(
                'Неожиданная ошибка при обновлении данных пользователя: '
                f'{error}'
            )
            return {}
