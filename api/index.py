from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .users import router as users_router
from .orders import router as orders_router

from payments import router as payments_router
app.include_router(payments_router, prefix="/api")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://accent-frontend.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router, prefix="/api")
app.include_router(orders_router, prefix="/api")
app.include_router(payments_router, prefix="/api")

@app.get("/")
def root():
    return {"status": "backend_alive"}

@app.get("/")
async def root():
    return {"status": "ok"}