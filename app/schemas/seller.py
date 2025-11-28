from pydantic import BaseModel

class SellerBase(BaseModel):
    name: str
    commision_percent: float

class SellerCreate(SellerBase):
    pass

class SellerRead(SellerBase):
    id: int

    orm_mode = True