from pydantic import BaseModel
from datetime import datetime
from backend.schemas.bid import SellerInterestOut
class PropertyIn(BaseModel):
    description: str
    location: str
    price: int
    property_type: str
    purpose: str
    is_available: bool = True

class SellerInterest(BaseModel):
    id: int
    property_id: int
    bid_amount: int | None
    counter_amount: int | None
    status: str

    class Config:
        from_attributes = True



class SellerPropertyOut(BaseModel):
    id: int
    location: str
    price: int
    property_type: str
    purpose: str
    is_available: bool
    interests: list[SellerInterest] = []

    class Config:
        from_attributes = True


# schemas/property.py

class BuyerPropertyOut(BaseModel):
    property_id: int
    description: str
    price_to_pay: int
    is_available: bool

    class Config:
        orm_mode = True

