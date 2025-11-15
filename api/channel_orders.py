from fastapi import APIRouter, HTTPException
import os
from supabase import create_client
import logging
import requests

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/create_channel_order")
async def create_channel_order(
    telegram_id: int,
    channel_username: str,
    price_ton: float
):
    """Создать ордер на продажу канала с подарками"""
    try:
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
        bot_token = os.environ.get("BOT_TOKEN")
        
        if not all([supabase_url, supabase_key, bot_token]):
            raise HTTPException(status_code=500, detail="Server configuration error")
        
        supabase = create_client(supabase_url, supabase_key)
        
        # 1. Проверяем права бота в канале
        bot_info_url = f"https://api.telegram.org/bot{bot_token}/getMe"
        bot_response = requests.get(bot_info_url)
        
        if bot_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Не удалось получить информацию о боте")
        
        bot_user_id = bot_response.json()["result"]["id"]
        
        # Проверяем права бота в канале
        chat_member_url = f"https://api.telegram.org/bot{bot_token}/getChatMember"
        params = {
            "chat_id": channel_username,
            "user_id": bot_user_id
        }
        member_response = requests.get(chat_member_url, params=params)
        
        if member_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Канал не найден или бот не имеет доступа")
        
        member_info = member_response.json()
        status = member_info["result"]["status"]
        
        if status not in ["administrator", "creator"]:
            raise HTTPException(status_code=400, detail="Бот не является администратором канала")
        
        # 2. Получаем информацию о канале
        chat_info_url = f"https://api.telegram.org/bot{bot_token}/getChat"
        chat_params = {"chat_id": channel_username}
        chat_response = requests.get(chat_info_url, params=chat_params)
        
        if chat_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Не удалось получить информацию о канале")
        
        channel_info = chat_response.json()["result"]
        channel_title = channel_info.get("title", "Неизвестный канал")
        
        # 3. В реальной реализации здесь мы бы получали реальные подарки канала
        # Сейчас используем демо-данные, которые потом заменим на реальные
        demo_gifts = [
            {"name": "Rose", "emoji": "🌹", "type": "premium_gift"},
            {"name": "Crown", "emoji": "👑", "type": "premium_gift"},
            {"name": "Fire", "emoji": "🔥", "type": "premium_gift"}
        ]
        
        # 4. Проверяем, что канал еще не выставлен на продажу
        existing_order = supabase.table("orders")\
            .select("*")\
            .eq("channel_username", channel_username)\
            .eq("status", "active")\
            .execute()
        
        if existing_order.data:
            raise HTTPException(status_code=400, detail="Этот канал уже выставлен на продажу")
        
        # 5. Создаем ордер
        new_order = {
            "seller_id": telegram_id,
            "gift_type": "channel",
            "gift_name": channel_title,
            "price_ton": price_ton,
            "channel_link": f"https://t.me/{channel_username.replace('@', '')}",
            "channel_username": channel_username,
            "channel_gifts": demo_gifts,  # Сохраняем подарки канала
            "status": "active"
        }
        
        result = supabase.table("orders").insert(new_order).execute()
        
        if result.data:
            return {
                "status": "success",
                "message": "Канал успешно выставлен на продажу",
                "order": result.data[0]
            }
        else:
            raise HTTPException(status_code=500, detail="Не удалось создать ордер")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_channel_order: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при создании ордера: {str(e)}")

@router.get("/market_channel_orders")
async def get_market_channel_orders():
    """Получить все активные ордера на каналы"""
    try:
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            raise HTTPException(status_code=500, detail="Server configuration error")
        
        supabase = create_client(supabase_url, supabase_key)
        
        # Получаем активные ордера на каналы
        response = supabase.table("orders")\
            .select("*, users!orders_seller_id_fkey(username, first_name)")\
            .eq("gift_type", "channel")\
            .eq("status", "active")\
            .execute()
        
        return {
            "status": "success",
            "orders": response.data
        }
        
    except Exception as e:
        logger.error(f"Error in get_market_channel_orders: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения ордеров: {str(e)}")

@router.post("/buy_channel_order")
async def buy_channel_order(order_id: int, buyer_telegram_id: int):
    """Купить канал (изменить владельца)"""
    try:
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            raise HTTPException(status_code=500, detail="Server configuration error")
        
        supabase = create_client(supabase_url, supabase_key)
        
        # 1. Получаем информацию об ордере
        order_response = supabase.table("orders")\
            .select("*")\
            .eq("id", order_id)\
            .eq("status", "active")\
            .execute()
        
        if not order_response.data:
            raise HTTPException(status_code=404, detail="Ордер не найден")
        
        order = order_response.data[0]
        
        # 2. Проверяем, что покупатель не является продавцом
        if order["seller_id"] == buyer_telegram_id:
            raise HTTPException(status_code=400, detail="Нельзя купить свой же канал")
        
        # 3. Обновляем статус ордера
        update_order_response = supabase.table("orders")\
            .update({
                "status": "completed",
                "buyer_id": buyer_telegram_id,
                "completed_at": "now()"
            })\
            .eq("id", order_id)\
            .execute()
        
        # 4. В реальной реализации здесь будет передача прав на канал
        # Пока просто отмечаем ордер как выполненный
        
        return {
            "status": "success",
            "message": "Канал успешно куплен! Свяжитесь с продавцом для передачи прав.",
            "order": update_order_response.data[0] if update_order_response.data else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in buy_channel_order: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при покупке канала: {str(e)}")
