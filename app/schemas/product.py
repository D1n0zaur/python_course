from pydantic import BaseModel

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