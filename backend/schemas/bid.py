from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional,Literal,List

class InterestCreate(BaseModel):
    bid_amount: Optional[int] = None
    message: Optional[str] = None

class InterestUpdate(BaseModel):
    action: Literal["reject", "counter", "withdraw","accept_counter","reject_counter","accept_bid"]
    counter_amount: Optional[int]
class BuyerInterestOut(BaseModel):
    interest_id: int
    property_id: int
    bid_amount: int | None
    counter_amount: int | None
    price_to_pay: int
    status: str

    class Config:
        from_attributes = True

class SellerInterestOut(BaseModel):
     interest_id: int
     property_id: int
     base_price: int
     bid_amount: int|None
     counter_amount: int|None
     status: str

     class Config:
         from_attributes=True

