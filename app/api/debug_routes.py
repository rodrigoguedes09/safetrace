"""
Debug endpoint para testar autenticação
Adicione ao main.py temporariamente
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

debug_router = APIRouter(prefix="/debug", tags=["Debug"])


class TestRegister(BaseModel):
    email: str
    password: str
    full_name: str


@debug_router.post("/test-register")
async def test_register(data: TestRegister):
    """Endpoint de teste para registro."""
    try:
        from app.api.dependencies import get_auth_service
        from app.models.auth import UserCreate
        
        # Get auth service
        auth_service = None
        async for service in get_auth_service():
            auth_service = service
            break
        
        if not auth_service:
            return {"error": "Auth service not available"}
        
        # Try to create user
        try:
            user_data = UserCreate(
                email=data.email,
                full_name=data.full_name,
                password=data.password
            )
            
            user = await auth_service.create_user(user_data)
            
            return {
                "success": True,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "full_name": user.full_name
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "type": type(e).__name__
            }
            
    except Exception as e:
        return {
            "error": "Fatal error",
            "detail": str(e),
            "type": type(e).__name__
        }


@debug_router.post("/test-login")
async def test_login(email: str, password: str):
    """Endpoint de teste para login."""
    try:
        from app.api.dependencies import get_auth_service
        
        # Get auth service
        auth_service = None
        async for service in get_auth_service():
            auth_service = service
            break
        
        if not auth_service:
            return {"error": "Auth service not available"}
        
        # Get user
        user_in_db = await auth_service.get_user_by_email(email)
        
        if not user_in_db:
            return {
                "success": False,
                "error": "User not found"
            }
        
        # Verify password
        is_valid = auth_service.verify_password(password, user_in_db.hashed_password)
        
        return {
            "success": is_valid,
            "user": {
                "id": str(user_in_db.id),
                "email": user_in_db.email,
                "is_active": user_in_db.is_active
            } if is_valid else None,
            "password_verified": is_valid
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "type": type(e).__name__
        }


@debug_router.get("/test-db")
async def test_db():
    """Testa conexão com o banco."""
    try:
        from app.api.dependencies import get_db_pool
        from app.config import get_settings
        
        settings = get_settings()
        pool = await get_db_pool(settings)
        
        async with pool.acquire() as conn:
            # Test query
            result = await conn.fetchval("SELECT 1")
            
            # Check if tables exist
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            
            table_names = [row['table_name'] for row in tables]
            
            return {
                "success": True,
                "db_test": result,
                "tables": table_names,
                "has_users_table": "users" in table_names,
                "has_api_keys_table": "api_keys" in table_names
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "type": type(e).__name__
        }
