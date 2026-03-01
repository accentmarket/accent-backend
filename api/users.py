from fastapi import APIRouter, Depends
from .auth import get_current_user
from .database import get_supabase

router = APIRouter()


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    supabase = get_supabase()

    # рассчитываем баланс через ledger
    ledger = supabase.table("ledger") \
        .select("amount") \
        .eq("user_id", current_user["id"]) \
        .execute()

    balance = sum(float(entry["amount"]) for entry in ledger.data) if ledger.data else 0

    return {
        "id": current_user["id"],
        "telegram_id": current_user["telegram_id"],
        "username": current_user.get("username"),
        "first_name": current_user.get("first_name"),
        "balance": balance
    }
