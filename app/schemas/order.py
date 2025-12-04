from pydantic import BaseModel
from typing import List
from datetime import datetime

class OrderBase(BaseModel):
    seller_id: int
    total: float

class OrderCreate(OrderBase):
    pass

class OrderRead(OrderBase):
    id: int
    user_id: int
    created_at: datetime
    order_items: List['OrderItemRead'] = []

    class Config:
        orm_mode = True

from .order_item import OrderItemRead
OrderRead.update_forward_refs()