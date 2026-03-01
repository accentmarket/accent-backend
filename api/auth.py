import hashlib
import hmac
import os
import json
from urllib.parse import parse_qsl
from fastapi import Header, HTTPException, Depends
from .database import get_supabase


BOT_TOKEN = os.environ.get("BOT_TOKEN")


def validate_telegram_init_data(init_data: str) -> dict:
    if not init_data:
        raise HTTPException(status_code=401, detail="Missing initData")

    parsed_data = dict(parse_qsl(init_data, strict_parsing=True))

    hash_received = parsed_data.pop("hash", None)
    if not hash_received:
        raise HTTPException(status_code=401, detail="Invalid initData")

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed_data.items())
    )

    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()

    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, hash_received):
        raise HTTPException(status_code=401, detail="Invalid Telegram signature")

    return parsed_data


def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    init_data = authorization.replace("Bearer ", "")
    data = validate_telegram_init_data(init_data)

    user_json = data.get("user")
    if not user_json:
        raise HTTPException(status_code=401, detail="User not found")

    telegram_user = json.loads(user_json)
    telegram_id = telegram_user["id"]

    supabase = get_supabase()

    response = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()

    if response.data:
        return response.data[0]

    # создаем пользователя
    new_user = {
        "telegram_id": telegram_id,
        "username": telegram_user.get("username"),
        "first_name": telegram_user.get("first_name")
    }

    result = supabase.table("users").insert(new_user).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create user")

    return result.data[0]
