from pydantic import BaseModel
from datetime import datetime
from backend.schemas.bid import SellerInterestOut
from enum import Enum
from typing import Optional

class PropertyPurpose(str, Enum):
    buy = "buy"
    rent = "rent"

class PropertyType(str, Enum):
    apartment = "apartment"
    house = "house"
    flat="flat"
    plot = "plot"
    commercial = "commercial"

class LocationIn(BaseModel):
    city: str
    state: str
    pincode: str

class PropertyIn(BaseModel):
    description: str
    city: str
    state: str
    pincode: str
    price: int
    property_type: PropertyType
    purpose: PropertyPurpose
    is_available: bool = True

class SellerInterest(BaseModel):
    id: int
    property_id: int
    bid_amount: int | None
    counter_amount: int | None
    status: str

    class Config:
        from_attributes = True

class LocationOut(BaseModel):
    city: str
    state: str
    pincode: str

    class Config:
        from_attributes = True

class SellerPropertyOut(BaseModel):
    id: int
    location: LocationOut
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
        from_attributes = True

class PropertyUpdate(BaseModel):
    price: Optional[int] = None
    description: Optional[str] = None
    property_type: Optional[PropertyType] = None
    purpose: Optional[PropertyPurpose] = None