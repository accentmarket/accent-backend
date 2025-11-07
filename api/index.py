# api/index.py
import os
import importlib
from http import HTTPStatus

def handler(request, context):
    # Определяем путь и метод запроса
    path = request.path
    method = request.method.lower()
    
    try:
        # Маршрутизация запросов
        if path.startswith('/api/user') and method == 'get':
            module = importlib.import_module('api.user')
            return module.handler(request, context)
        
        elif path.startswith('/api/channels') and method == 'post':
            module = importlib.import_module('api.channels')
            return module.handler(request, context)
        
        # Если эндпоинт не найден
        return {
            'error': 'Endpoint not found'
        }, HTTPStatus.NOT_FOUND
    
    except Exception as e:
        return {
            'error': f'Internal server error: {str(e)}'
        }, HTTPStatus.INTERNAL_SERVER_ERROR