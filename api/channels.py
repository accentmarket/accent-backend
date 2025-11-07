# api/channels.py
import os
import requests
from http import HTTPStatus

# Получаем переменные окружения
SUPABASE_URL = "https://kftukrpznzvdvsimsywbl.supabase.co"
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
BOT_TOKEN = os.environ.get('BOT_TOKEN')

def validate_telegram_data(init_data: str) -> dict:
    """Валидация данных от Telegram WebApp"""
    try:
        import urllib.parse
        import hmac
        import hashlib
        import time
        
        params = {}
        for part in init_data.split("&"):
            if "=" in part:
                key, value = part.split("=", 1)
                params[key] = urllib.parse.unquote(value)
        
        # Проверка срока действия (24 часа)
        if "auth_date" in params:
            if time.time() - int(params["auth_date"]) > 86400:
                raise Exception("Data expired")
        
        # Проверка хеша
        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()) if k != "hash")
        hash_computed = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
        
        if hash_computed != params.get("hash"):
            raise Exception("Invalid hash")
        
        return params
    except Exception as e:
        raise Exception(f"Validation failed: {str(e)}")

def handler(request, context):
    try:
        # Получаем данные из тела запроса
        body = request.json
        init_data = body.get('initData')
        channel_username = body.get('channel_username')
        
        if not init_data or not channel_username:
            return {'error': 'initData and channel_username are required'}, HTTPStatus.BAD_REQUEST
        
        # Валидация данных
        try:
            user_data = validate_telegram_data(init_data)
            user = eval(user_data["user"])
            telegram_id = int(user["id"])
        except Exception as e:
            return {'error': str(e)}, HTTPStatus.UNAUTHORIZED
        
        # Проверяем формат юзернейма
        if not channel_username.startswith('@'):
            return {'error': 'Channel username must start with @'}, HTTPStatus.BAD_REQUEST
        
        # Проверяем, не добавлен ли уже этот канал
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        
        check_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/channels?telegram_id=eq.{telegram_id}&channel_username=eq.{channel_username}",
            headers=headers
        )
        
        if check_response.status_code != 200:
            return {'error': 'Database error'}, HTTPStatus.INTERNAL_SERVER_ERROR
        
        existing_channels = check_response.json()
        if existing_channels:
            return {'error': 'This channel is already added'}, HTTPStatus.BAD_REQUEST
        
        # Добавляем канал в базу
        new_channel = {
            "telegram_id": telegram_id,
            "channel_username": channel_username,
            "status": "active"
        }
        
        create_response = requests.post(
            f"{SUPABASE_URL}/rest/v1/channels",
            headers=headers,
            json=new_channel
        )
        
        if create_response.status_code not in [200, 201]:
            return {'error': 'Failed to add channel'}, HTTPStatus.INTERNAL_SERVER_ERROR
        
        return {
            'message': 'Channel successfully added',
            'channel': channel_username
        }, HTTPStatus.OK
    
    except Exception as e:
        return {'error': str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR