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

@router.patch("/{deal_id}/pay")
def confirm_payment(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(404, "Deal not found")
    if deal.buyer_id != current_user.id:
        raise HTTPException(403, "Only the buyer can confirm payment")
    if deal.status != "documents_verified":
        raise HTTPException(400, f"Cannot pay at this stage. Current status: {deal.status}")

    deal.status = "payment_pending"
    db.commit()
    return {"message": "Payment confirmed by buyer, awaiting agent approval", "deal_status": deal.status}


@router.patch("/{deal_id}/complete")
def complete_deal(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.require_agent)
):
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(404, "Deal not found")

    agent = db.query(models.Agent).filter(models.Agent.user_id == current_user.id).first()
    if deal.agent_id != agent.id:
        raise HTTPException(403, "Not your deal")
    if deal.status != "payment_pending":
        raise HTTPException(400, f"Cannot complete at this stage. Current status: {deal.status}")

    deal.status = "completed"

    # mark property as sold
    property = db.query(models.Property).filter(models.Property.id == deal.property_id).first()
    if property:
        property.is_available = False

    db.commit()
    return {"message": "Deal completed successfully", "deal_status": deal.status}