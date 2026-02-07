from fastapi import APIRouter, HTTPException
import os
from supabase import create_client
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/channels")
async def add_channel(telegram_id: int, channel_username: str):
    try:
        logger.info(f"Adding channel {channel_username} for user {telegram_id}")
        
        # Инициализация Supabase
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            raise HTTPException(status_code=500, detail="Server configuration error")
        
        supabase = create_client(supabase_url, supabase_key)
        
        # Проверяем валидность юзернейма
        if not channel_username.startswith('@'):
            raise HTTPException(status_code=400, detail="Юзернейм канала должен начинаться с @")
        
        # Проверяем, не добавлен ли уже этот канал
        existing = supabase.table("channels").select("*").eq("channel_username", channel_username).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Этот канал уже добавлен")
        
        # Добавляем канал
        new_channel = {
            "telegram_id": telegram_id,
            "channel_username": channel_username,
            "status": "active"
        }
        result = supabase.table("channels").insert(new_channel).execute()
        
        if result.data:
            return {
                "message": "Канал успешно добавлен",
                "channel": channel_username
            }
        else:
            raise HTTPException(status_code=500, detail="Не удалось добавить канал")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in add_channel: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при добавлении канала: {str(e)}")
