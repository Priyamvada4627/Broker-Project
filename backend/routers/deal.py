from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, oauth2
from ..schemas import deal
from ..database import get_db

router = APIRouter(
    prefix="/deals",
    tags=["Deals"]
)

@router.get("/my",response_model=list[deal.Deal_Out])
def get_my_deals(
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    deals = db.query(models.Deal).filter(
        (models.Deal.buyer_id == current_user.id) |
        (models.Deal.seller_id == current_user.id)
    ).all()

    response = []
    for deal in deals:
        response.append({
            "deal_id": deal.id,
            "property_id": deal.property_id,
            "seller_price": deal.seller_price,
            "agent_id":deal.agent_id,
            "agent_fee": deal.agent_fee,
            "final_price": deal.final_price,
            "status": deal.status,
            "created_at": deal.created_at
        })

    return response