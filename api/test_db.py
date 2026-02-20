from fastapi import APIRouter
import os
from supabase import create_client
import logging

router = APIRouter()
# Исправлено: __name__
logger = logging.getLogger(__name__)

@router.get("/test_db")
async def test_db():
    try:
        logger.info("Testing database connection")
        
        # Исправлено: убраны пробелы в названиях переменных
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")  # Лучше использовать SUPABASE_KEY
        
        if not supabase_url or not supabase_key:
            return {
                "status": "error",
                "error": "Environment variables not set",
                "supabase_url_set": bool(supabase_url),
                "supabase_key_set": bool(supabase_key)
            }
        
        supabase = create_client(supabase_url, supabase_key)
        
        # Исправлено: убраны пробелы в названии таблицы
        response = supabase.table('users').select('*').limit(2).execute()
        
        tables = ['users', 'channels', 'transactions']
        table_status = {}
         
        for table in tables:
            try:
                test_response = supabase.table(table).select('id').limit(1).execute()
                table_status[table] = "exists"
            except Exception as e:
                table_status[table] = f"error: {str(e)}"
        
        return {
            "status": "success",
            "supabase_url": supabase_url[:20] + "..." if supabase_url else "not_set",
            "tables_status": table_status,
            "sample_users": response.data
        }
        
    except Exception as e:
        logger.error(f"Error in test_db: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }