from sqlalchemy import Column, Integer, String, Float
from app.database import Base

class Seller(Base):
    __tablename__ = "sellers"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    commission_percent = Column(Float, nullable=False)