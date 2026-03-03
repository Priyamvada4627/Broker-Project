from pydantic import BaseModel, EmailStr
from datetime import datetime
class Deal_Out(BaseModel):
    deal_id: int
    property_id: int
    seller_price: int
    agent_id: int
    agent_fee:int
    final_price: int
    status: str
    created_at: datetime
    class Config:
        from_attributes = True

        
