from fastapi import FastAPI, HTTPException, Request
import httpx
import hashlib
import hmac
import time
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Supabase и Telegram
SUPABASE_URL = "https://kftukrpznzvdvsimsywbl.supabase.co"
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")

def validate_telegram_data(init_data: str) -> dict:
    try:
        params = {}
        for part in init_data.split("&"):
            if "=" in part:
                key, value = part.split("=", 1)
                params[key] = value

        if "auth_date" in params:
            if time.time() - int(params["auth_date"]) > 86400:
                raise Exception("Expired")

        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()) if k != "hash")
        hash_ = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()

        if hash_ != params.get("hash"):
            raise Exception("Invalid hash")

        return params
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Validation failed: {str(e)}")

@app.post("/create_order")
async def create_order(request: Request):
    data = await request.json()
    init_data = data.get("initData")
    order = data.get("order")

    if not init_data or not order:
        raise HTTPException(status_code=400, detail="Missing initData or order")

    user_data = validate_telegram_data(init_data)
    user = eval(user_data["user"])  # Telegram передаёт user как строку-словарь
    telegram_id = int(user["id"])

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SUPABASE_URL}/rest/v1/orders",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "seller_id": telegram_id,
                "gift_type": order["gift_type"],
                "gift_name": order["gift_name"],
                "price_ton": order["price_ton"],
                "channel_link": order.get("channel_link"),
                "status": "active"
            }
        )
        if response.status_code not in (200, 201):
            raise HTTPException(status_code=500, detail="Failed to save order")

    return {"ok": True}
