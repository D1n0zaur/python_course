from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.jwt_manager import jwt_manager

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> int:
    """
    Зависимость для получения текущего пользователя из JWT токена
    """
    token = credentials.credentials
    user_id = jwt_manager.get_user_id_from_token(token)
    
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Невалидный или истекший токен",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id

async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Зависимость для проверки, что пользователь - админ
    """
    token = credentials.credentials
    payload = jwt_manager.verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Невалидный токен"
        )
    
    if not payload.get("is_admin"):
        raise HTTPException(
            status_code=403,
            detail="Требуются права администратора"
        )
    
    return {
        "user_id": int(payload.get("sub")),
        "username": payload.get("username"),
        "is_admin": True
    }