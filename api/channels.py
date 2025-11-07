import os
import requests
from http import HTTPStatus
from fastapi import FastAPI, HTTPException

app = FastAPI()

SUPABASE_URL = "https://kftukrpznzvdvsimsywbl.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

@app.post("/channels")
async def add_channel(request: dict):
    try:
        telegram_id = request.get("telegram_id")
        channel_username = request.get("channel_username")
        
        if not telegram_id or not channel_username:
            raise HTTPException(status_code=400, detail="Отсутствуют необходимые данные")
        
        if not channel_username.startswith('@'):
            raise HTTPException(status_code=400, detail="Некорректный формат юзернейма канала")
        
        # Проверяем, есть ли уже такой канал у пользователя
        existing_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/channels?telegram_id=eq.{telegram_id}&channel_username=eq.{channel_username}",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
        )
        
        if existing_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Ошибка при проверке канала")
        
        existing_channels = existing_response.json()
        if existing_channels:
            raise HTTPException(status_code=400, detail="Этот канал уже добавлен")
        
        # Добавляем новый канал
        new_channel = {
            "telegram_id": telegram_id,
            "channel_username": channel_username,
            "status": "active"
        }
        
        create_response = requests.post(
            f"{SUPABASE_URL}/rest/v1/channels",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            },
            json=new_channel
        )
        
        if create_response.status_code != 201:
            raise HTTPException(status_code=500, detail="Не удалось добавить канал")
        
        return {"message": "Канал успешно добавлен"}, HTTPStatus.OK
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")
