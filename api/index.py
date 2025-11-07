# api/index.py
import json
from http import HTTPStatus

def handler(request, context):
    # Простой тестовый эндпоинт
    return {
        "message": "Hello from Accent Backend!",
        "path": request.path,
        "method": request.method
    }, HTTPStatus.OK