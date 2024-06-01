import os
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv('API_TOKEN')
JETADMIN_API_KEY = os.getenv('JETADMIN_API_KEY')
API_URL_POST = os.getenv('API_URL_POST')
API_URL_USER = os.getenv('API_URL_USER')

HEADERS = {
    'Authorization': f'Bearer {JETADMIN_API_KEY}',
    'Content-Type': 'application/json'
}
