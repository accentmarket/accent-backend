from fastapi import APIRouter, HTTPException
import os
from supabase import create_client
import logging
import requests
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/create_order")
async def create_order(
    telegram_id: int,
    channel_username: str,
    price_ton: float,
    gift_type: str = "channel"
):
    """Создать ордер на продажу канала"""
    try:
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
        bot_token = os.environ.get("BOT_TOKEN")
        
        if not all([supabase_url, supabase_key]):
            raise HTTPException(status_code=500, detail="Server configuration error")
        
        supabase = create_client(supabase_url, supabase_key)
        
        # 1. Проверяем, что пользователь существует
        user_response = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
        if not user_response.data:
            raise HTTPException(status_code=400, detail="Пользователь не найден")
        
        user = user_response.data[0]
        
        # 2. Проверяем, что канал не уже выставлен на продажу
        existing_order = supabase.table("orders")\
            .select("*")\
            .eq("channel_username", channel_username)\
            .eq("status", "active")\
            .execute()
        
        if existing_order.data:
            raise HTTPException(status_code=400, detail="Этот канал уже выставлен на продажу")
        
        # 3. Получаем информацию о канале (если бот токен есть)
        channel_title = channel_username
        channel_gifts = []
        
        if bot_token:
            try:
                chat_info_url = f"https://api.telegram.org/bot{bot_token}/getChat"
                chat_params = {"chat_id": channel_username}
                chat_response = requests.get(chat_info_url, params=chat_params)
                
                if chat_response.status_code == 200:
                    channel_info = chat_response.json()["result"]
                    channel_title = channel_info.get("title", channel_username)
                    
                    # Здесь в будущем будет логика получения реальных подарков канала
                    # Сейчас используем демо-подарки
                    channel_gifts = [
                        {"name": "Rose", "emoji": "🌹", "type": "premium_gift"},
                        {"name": "Crown", "emoji": "👑", "type": "premium_gift"},
                        {"name": "Star", "emoji": "⭐", "type": "premium_gift"}
                    ]
                    
            except Exception as e:
                logger.warning(f"Не удалось получить информацию о канале: {e}")
        
        # 4. Создаем ордер
        new_order = {
            "seller_id": telegram_id,
            "gift_type": gift_type,
            "gift_name": channel_title,
            "price_ton": price_ton,
            "channel_link": f"https://t.me/{channel_username.replace('@', '')}",
            "channel_username": channel_username,
            "channel_gifts": channel_gifts,  # Сохраняем подарки канала
            "status": "active",
            "created_at": datetime.now().isoformat()
        }
        
        result = supabase.table("orders").insert(new_order).execute()
        
        if result.data:
            logger.info(f"Создан новый ордер: {result.data[0]['id']} для канала {channel_username}")
            return {
                "status": "success",
                "message": "Ордер успешно создан",
                "order": result.data[0]
            }
        else:
            raise HTTPException(status_code=500, detail="Не удалось создать ордер")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_order: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при создании ордера: {str(e)}")

@router.get("/market_orders")
async def get_market_orders(gift_type: str = "channel"):
    """Получить активные ордера для маркета"""
    try:
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            raise HTTPException(status_code=500, detail="Server configuration error")
        
        supabase = create_client(supabase_url, supabase_key)
        
        # Получаем активные ордера с информацией о продавцах
        response = supabase.table("orders")\
            .select("*, users!orders_seller_id_fkey(username, first_name, telegram_id)")\
            .eq("status", "active")\
            .eq("gift_type", gift_type)\
            .order("created_at", desc=True)\
            .execute()
        
        return {
            "status": "success",
            "orders": response.data
        }
        
    except Exception as e:
        logger.error(f"Error in get_market_orders: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения ордеров: {str(e)}")

@router.get("/my_orders")
async def get_my_orders(telegram_id: int):
    """Получить ордера пользователя"""
    try:
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            raise HTTPException(status_code=500, detail="Server configuration error")
        
        supabase = create_client(supabase_url, supabase_key)
        
        # Ордера где пользователь продавец
        seller_orders = supabase.table("orders")\
            .select("*")\
            .eq("seller_id", telegram_id)\
            .order("created_at", desc=True)\
            .execute()
        
        # Ордера где пользователь покупатель
        buyer_orders = supabase.table("orders")\
            .select("*")\
            .eq("buyer_id", telegram_id)\
            .order("created_at", desc=True)\
            .execute()
        
        return {
            "status": "success",
            "seller_orders": seller_orders.data,
            "buyer_orders": buyer_orders.data
        }
        
    except Exception as e:
        logger.error(f"Error in get_my_orders: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения ордеров: {str(e)}")

@router.post("/cancel_order")
async def cancel_order(order_id: int, telegram_id: int):
    """Отменить ордер"""
    try:
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            raise HTTPException(status_code=500, detail="Server configuration error")
        
        supabase = create_client(supabase_url, supabase_key)
        
        # Проверяем, что ордер существует и принадлежит пользователю
        order_response = supabase.table("orders")\
            .select("*")\
            .eq("id", order_id)\
            .eq("seller_id", telegram_id)\
            .eq("status", "active")\
            .execute()
        
        if not order_response.data:
            raise HTTPException(status_code=404, detail="Ордер не найден или у вас нет прав для его отмены")
        
        # Обновляем статус ордера
        update_response = supabase.table("orders")\
            .update({
                "status": "cancelled",
                "updated_at": datetime.now().isoformat()
            })\
            .eq("id", order_id)\
            .execute()
        
        if update_response.data:
            logger.info(f"Ордер {order_id} отменен пользователем {telegram_id}")
            return {
                "status": "success",
                "message": "Ордер успешно отменен"
            }
        else:
            raise HTTPException(status_code=500, detail="Не удалось отменить ордер")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in cancel_order: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при отмене ордера: {str(e)}")
