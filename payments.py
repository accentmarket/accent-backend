from fastapi import APIRouter, HTTPException, Request
from decimal import Decimal
from .database import get_supabase
import os

router = APIRouter()

TON_WALLET = os.environ.get("TON_WALLET")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")


@router.post("/payments/webhook")
async def ton_webhook(request: Request):

    # 1️⃣ Проверка secret header
    if WEBHOOK_SECRET:
        if request.headers.get("X-Webhook-Secret") != WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="Invalid webhook signature")

    data = await request.json()

    # 2️⃣ Парсинг payload (TonAPI format)
    try:
        tx = data["transaction"]
        tx_hash = tx["hash"]

        in_msg = tx["in_msg"]

        value_raw = in_msg["value"]              # в nanoTON
        destination = in_msg["destination"]
        comment = in_msg.get("message", "")

        amount = Decimal(value_raw) / Decimal(10**9)

    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload structure")

    # 3️⃣ Проверяем получателя
    if destination != TON_WALLET:
        raise HTTPException(status_code=400, detail="Wrong recipient")

    # 4️⃣ Проверяем comment
    if not comment.startswith("deposit_"):
        raise HTTPException(status_code=400, detail="Invalid deposit comment")

    try:
        telegram_id = int(comment.replace("deposit_", ""))
    except:
        raise HTTPException(status_code=400, detail="Invalid telegram id in comment")

    supabase = get_supabase()

    # 5️⃣ Проверка дубликата транзакции
    existing = (
        supabase
        .table("deposits")
        .select("id")
        .eq("tx_hash", tx_hash)
        .execute()
    )

    if existing.data:
        return {"status": "already_processed"}

    # 6️⃣ Ищем пользователя
    user_resp = (
        supabase
        .table("users")
        .select("*")
        .eq("telegram_id", telegram_id)
        .execute()
    )

    if not user_resp.data:
        raise HTTPException(status_code=404, detail="User not found")

    user = user_resp.data[0]

    # 7️⃣ Сохраняем депозит
    supabase.table("deposits").insert({
        "tx_hash": tx_hash,
        "telegram_id": telegram_id,
        "amount": str(amount)
    }).execute()

    # 8️⃣ Записываем в ledger
    supabase.table("ledger").insert({
        "user_id": user["id"],
        "amount": str(amount),
        "type": "deposit"
    }).execute()

    return {"status": "credited"}