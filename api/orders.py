from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from decimal import Decimal
from .auth import get_current_user
from .database import get_supabase

router = APIRouter()


# ======================
# Schemas
# ======================

class CreateOrderRequest(BaseModel):
    channel_username: str = Field(..., min_length=3)
    price_ton: Decimal = Field(..., gt=0)


# ======================
# Create Order
# ======================

@router.post("/orders")
async def create_order(
    payload: CreateOrderRequest,
    current_user: dict = Depends(get_current_user)
):
    supabase = get_supabase()

    # Проверка существования активного ордера
    existing = supabase.table("orders") \
        .select("id") \
        .eq("channel_username", payload.channel_username) \
        .eq("status", "active") \
        .execute()

    if existing.data:
        raise HTTPException(status_code=400, detail="Channel already listed")

    new_order = {
        "seller_id": current_user["id"],
        "channel_username": payload.channel_username,
        "price_ton": str(payload.price_ton),
        "status": "active"
    }

    result = supabase.table("orders").insert(new_order).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create order")

    return {"order": result.data[0]}


# ======================
# Buy Order (Escrow Hold)
# ======================

@router.post("/orders/{order_id}/buy")
async def buy_order(
    order_id: int,
    current_user: dict = Depends(get_current_user)
):
    supabase = get_supabase()

    # Получаем ордер
    order_resp = supabase.table("orders") \
        .select("*") \
        .eq("id", order_id) \
        .execute()

    if not order_resp.data:
        raise HTTPException(status_code=404, detail="Order not found")

    order = order_resp.data[0]

    if order["status"] != "active":
        raise HTTPException(status_code=400, detail="Order not active")

    if order["seller_id"] == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot buy your own order")

    # Получаем баланс через ledger
    ledger_resp = supabase.table("ledger") \
        .select("amount") \
        .eq("user_id", current_user["id"]) \
        .execute()

    balance = sum(Decimal(entry["amount"]) for entry in ledger_resp.data) if ledger_resp.data else Decimal(0)

    price = Decimal(order["price_ton"])

    if balance < price:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    # Удержание средств
    hold_insert = supabase.table("ledger").insert({
        "user_id": current_user["id"],
        "order_id": order_id,
        "amount": str(-price),
        "type": "hold"
    }).execute()

    if not hold_insert.data:
        raise HTTPException(status_code=500, detail="Failed to hold funds")

    # Обновляем ордер ТОЛЬКО если он все еще active
    update = supabase.table("orders") \
        .update({
            "status": "escrow",
            "buyer_id": current_user["id"],
            "escrow_until": (datetime.utcnow() + timedelta(minutes=90)).isoformat()
        }) \
        .eq("id", order_id) \
        .eq("status", "active") \
        .execute()

    if not update.data:
        # если кто-то успел купить раньше — откатываем hold
        supabase.table("ledger").insert({
            "user_id": current_user["id"],
            "order_id": order_id,
            "amount": str(price),
            "type": "refund"
        }).execute()

        raise HTTPException(status_code=400, detail="Order already taken")

    return {"status": "escrow_started"}

# ======================
# Confirm Order (Release to Seller)
# ======================

@router.post("/orders/{order_id}/confirm")
async def confirm_order(
    order_id: int,
    current_user: dict = Depends(get_current_user)
):
    supabase = get_supabase()

    order_resp = supabase.table("orders") \
        .select("*") \
        .eq("id", order_id) \
        .execute()

    if not order_resp.data:
        raise HTTPException(status_code=404, detail="Order not found")

    order = order_resp.data[0]

    if order["status"] != "escrow":
        raise HTTPException(status_code=400, detail="Order not in escrow")

    if order["seller_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only seller can confirm")

    price = Decimal(order["price_ton"])

    # Перевод продавцу
    release = supabase.table("ledger").insert({
        "user_id": order["seller_id"],
        "order_id": order_id,
        "amount": str(price),
        "type": "release"
    }).execute()

    if not release.data:
        raise HTTPException(status_code=500, detail="Failed to release funds")

    # Обновляем статус
    update = supabase.table("orders") \
        .update({
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat()
        }) \
        .eq("id", order_id) \
        .eq("status", "escrow") \
        .execute()

    if not update.data:
        raise HTTPException(status_code=500, detail="Failed to complete order")

    return {"status": "completed"}

# ======================
# Cancel Order
# ======================

@router.post("/orders/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    current_user: dict = Depends(get_current_user)
):
    supabase = get_supabase()

    order_resp = supabase.table("orders") \
        .select("*") \
        .eq("id", order_id) \
        .execute()

    if not order_resp.data:
        raise HTTPException(status_code=404, detail="Order not found")

    order = order_resp.data[0]

    if order["seller_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only seller can cancel")

    if order["status"] != "active":
        raise HTTPException(status_code=400, detail="Only active orders can be cancelled")

    update = supabase.table("orders") \
        .update({
            "status": "cancelled"
        }) \
        .eq("id", order_id) \
        .eq("status", "active") \
        .execute()

    if not update.data:
        raise HTTPException(status_code=500, detail="Failed to cancel")

    return {"status": "cancelled"}
