from pydantic import BaseModel, EmailStr
from typing import Optional

class Token(BaseModel):
    """
    Схема для возврата токена
    """
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """
    Схема для данных в токене
    """
    user_id: Optional[int] = None
    username: Optional[str] = None

class LoginRequest(BaseModel):
    """
    Схема для запроса на вход
    """
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    """
    Схема для запроса на регистрацию
    """
    username: str
    email: EmailStr
    password: str