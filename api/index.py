from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Accent Market API")

# Разрешаем запросы от фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
from .user import router as user_router
# Временно отключаем отсутствующие роутеры
# from .channels import router as channels_router
# from .test_db import router as test_db_router

app.include_router(user_router, prefix="/api")
# app.include_router(channels_router, prefix="/api")
# app.include_router(test_db_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Accent Market Backend is running!", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "accent-market-backend"}