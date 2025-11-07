# api/user.py
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
        init_data = request.args.get('initData')
        if not init_data:
            return {'error': 'initData required'}, HTTPStatus.BAD_REQUEST
        
        # Валидация данных
        try:
            user_data = validate_telegram_data(init_data)
            user = eval(user_data["user"])  # Декодируем данные пользователя
            telegram_id = int(user["id"])
        except Exception as e:
            return {'error': str(e)}, HTTPStatus.UNAUTHORIZED
        
        # Получаем или создаем пользователя в Supabase
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        
        # Проверяем, существует ли пользователь
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{telegram_id}",
            headers=headers
        )
        
        if response.status_code != 200:
            return {'error': 'Database error'}, HTTPStatus.INTERNAL_SERVER_ERROR
        
        users = response.json()
        
        if not users:
            # Создаем нового пользователя
            new_user = {
                "telegram_id": telegram_id,
                "username": user.get("username", ""),
                "first_name": user.get("first_name", ""),
                "balance": 0.0
            }
            
            create_response = requests.post(
                f"{SUPABASE_URL}/rest/v1/users",
                headers=headers,
                json=new_user
            )
            
            if create_response.status_code not in [200, 201]:
                return {'error': 'Failed to create user'}, HTTPStatus.INTERNAL_SERVER_ERROR
            
            users = [new_user]
        
        # Возвращаем данные пользователя
        return {
            'telegram_id': users[0]['telegram_id'],
            'username': users[0]['username'],
            'balance': float(users[0]['balance'])
        }, HTTPStatus.OK
    
    except Exception as e:
        return {'error': str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR