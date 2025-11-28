from pydantic import BaseModel

class OrderItemBase(BaseModel):
    product_id: int
    quantity: int

class OrderItemCreate(OrderItemBase):
    order_id: int

class OrderItemRead(OrderItemBase):
    id: int
    order_id: int

    class Config:
        orm_mode = True