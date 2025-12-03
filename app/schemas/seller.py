from pydantic import BaseModel

class SellerBase(BaseModel):
    name: str
    commission_percent: float

class SellerCreate(SellerBase):
    pass

class SellerRead(SellerBase):
    id: int

    class Config:
        from_attributes = True