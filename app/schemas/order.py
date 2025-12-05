from pydantic import BaseModel
from typing import List
from datetime import datetime

class OrderBase(BaseModel):
    product_id: int
    count: int

class OrderCreate(OrderBase):
    pass

class OrderRead(OrderBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True