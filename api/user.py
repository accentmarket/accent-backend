import os
import requests
from http import HTTPStatus
from fastapi import FastAPI, HTTPException, Request

app = FastAPI()

SUPABASE_URL = "https://kftukrpznzvdvsimsywbl.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

@app.get("/user")
async def get_user(telegram_id: int):
    try:
        # Проверяем, существует ли пользователь
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{telegram_id}",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Ошибка базы данных")
        
        users = response.json()
        
        if not users:
            # Создаем нового пользователя
            new_user = {
                "telegram_id": telegram_id,
                "balance": 0.0
            }
            
            create_response = requests.post(
                f"{SUPABASE_URL}/rest/v1/users",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json=new_user
            )
            
            if create_response.status_code != 201:
                raise HTTPException(status_code=500, detail="Не удалось создать пользователя")
            
            users = create_response.json()
        
        return {
            "telegram_id": users[0]["telegram_id"],
            "balance": float(users[0]["balance"])
        }, HTTPStatus.OK
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")
