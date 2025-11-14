from fastapi import APIRouter, HTTPException
import os
from supabase import create_client
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/user")
async def get_user(telegram_id: int):
    try:
        logger.info(f"Getting user with telegram_id: {telegram_id}")
        
        # Инициализация Supabase
        supabase_url = os.environ.get("https://kftukrpnzvdvsimsywbl.supabase.co")
        supabase_key = os.environ.get("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtmdHVrcnBuenZkdnNpbXN5d2JsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MjAzNjI3NiwiZXhwIjoyMDc3NjEyMjc2fQ.YwsZjaZ50aV_nKnJTsZDG_5lo_uXbIIfBVvn1LMRWyU")
        
        if not supabase_url or not supabase_key:
            logger.error("Supabase credentials not set")
            raise HTTPException(status_code=500, detail="Server configuration error")
        
        supabase = create_client(supabase_url, supabase_key)
        
        # Проверяем существование пользователя
        response = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
        
        if response.data:
            logger.info(f"User found: {response.data[0]}")
            return response.data[0]
        else:
            # Создаем нового пользователя
            logger.info(f"Creating new user with telegram_id: {telegram_id}")
            new_user = {
                "telegram_id": telegram_id,
                "balance": 0.0
            }
            result = supabase.table("users").insert(new_user).execute()
            
            if result.data:
                logger.info(f"New user created: {result.data[0]}")
                return result.data[0]
            else:
                logger.error("Failed to create user")
                raise HTTPException(status_code=500, detail="Failed to create user")
                
    except Exception as e:
        logger.error(f"Error in get_user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")