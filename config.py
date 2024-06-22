import os
from dotenv import load_dotenv
from telegram.request import HTTPXRequest

# Загрузка переменных окружения из файла .env
load_dotenv()

# Получение значений переменных окружения
API_TOKEN = os.getenv('API_TOKEN')
JETADMIN_API_KEY = os.getenv('JETADMIN_API_KEY')
API_URL_POST = os.getenv('API_URL_POST')
API_URL_USER = os.getenv('API_URL_USER')

# Заголовки для запросов к API
HEADERS = {
    'Authorization': f'Bearer {JETADMIN_API_KEY}',
    'Content-Type': 'application/json'
}

# Настройка тайм-аутов и лимитов для HTTPXRequest
request = HTTPXRequest(
    connect_timeout=10.0,
    read_timeout=300.0,
    write_timeout=300.0,
    pool_timeout=5.0
)

# Убедитесь, что все необходимые переменные окружения загружены правильно
if not all([API_TOKEN, JETADMIN_API_KEY, API_URL_POST, API_URL_USER]):
    raise EnvironmentError(
        'Не удалось загрузить одну или несколько переменных окружения.'
        'Проверьте файл .env'
    )
