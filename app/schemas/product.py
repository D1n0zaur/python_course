from pydantic import BaseModel
from typing import Optional

class ProductBase(BaseModel):
    name: str
    price: float

class ProductCreate(ProductBase):
    seller_id: int

class ProductRead(ProductBase):
    id: int
    seller_id: int

    class Config:
        orm_mode = True

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    seller_id: Optional[int] = None

    class Config:
        orm_mode = True