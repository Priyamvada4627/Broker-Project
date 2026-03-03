from fastapi import APIRouter,Response,status,HTTPException,Depends,Query
from ..schemas import Property,bid
from ..database import get_db
from sqlalchemy.orm import Session
from .. import models,oauth2
from typing import List,Optional
from backend.services import pricing,deal
from backend.services.agent import get_platform_agent


router = APIRouter(
    prefix="/bid",
    tags=["Bid"]
)




@router.post("/{property_id}", status_code=201)
def create_interest(
    property_id: int,
    interest: bid.InterestCreate,  
    db: Session = Depends(get_db),
    current_user: int = Depends(oauth2.get_current_user)
):
    property = db.query(models.Property).filter(models.Property.id == property_id).first()

    if not property or not property.is_available:
        raise HTTPException(status_code=404, detail="Property not available")
    if property.seller_id == current_user.id:
        raise HTTPException(status_code=403, detail="You cannot bid on your own property")
    agent=agent=db.query(models.Agent).filter(models.Agent.id==property.agent_id).first()
    new_interest = models.Interest(
        property_id=property_id,
        buyer_id=current_user.id,
        bid_amount=interest.bid_amount,
        message=interest.message,
        agent_id=agent.id   
    )

    db.add(new_interest)
    db.commit()
    db.refresh(new_interest)

    return {
        "message": "Interest submitted successfully",
        "interest_id": new_interest.id
    }






@router.patch("/{interest_id}")
def update_interest(
    interest_id: int,
    payload: bid.InterestUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user),
):
    interest = db.query(models.Interest).filter(
        models.Interest.id == interest_id
    ).first()

    if not interest:
        raise HTTPException(404, "Interest not found")

    property_obj = db.query(models.Property).filter(
        models.Property.id == interest.property_id
    ).first()

    if not property_obj:
        raise HTTPException(404, "Property not found")

    if interest.status in ("accepted", "agreed", "rejected", "withdrawn"):
        raise HTTPException(
            status_code=400,
            detail="Interest is finalized and cannot be modified"
        )

    # ---------------- BUYER ACTIONS ----------------
    if payload.action in ("withdraw", "accept_counter", "reject_counter"):
        if interest.buyer_id != current_user.id:
            raise HTTPException(403, "Not allowed")

        if payload.action == "withdraw":
            if interest.status not in ["pending", "countered"]:
                raise HTTPException(400, "Cannot withdraw now")
            interest.status = "withdrawn"

        elif payload.action == "accept_counter":
            if interest.status != "countered":
                raise HTTPException(400, "No counter to accept")
            interest.status = "agreed"

        elif payload.action == "reject_counter":
            if interest.status != "countered":
                raise HTTPException(400, "No counter to reject")
            interest.status = "withdrawn"

    # ---------------- SELLER ACTIONS ----------------
    else:
        if property_obj.seller_id != current_user.id:
            raise HTTPException(403, "Not allowed")

        if payload.action == "accept_bid":
            
            if interest.status != "pending":
                raise HTTPException(400, "Cannot accept now")
   
            if interest.bid_amount is None:
                raise HTTPException(400, "Cannot accept a bid with no bid amount")

            interest.status = "accepted"

        elif payload.action == "counter":
            if interest.status != "pending":
                raise HTTPException(400, "Cannot counter now")
            if payload.counter_amount is None:
                raise HTTPException(400, "counter_amount required")
            interest.status = "countered"
            interest.counter_amount = payload.counter_amount

        elif payload.action == "reject":
            if interest.status not in ("pending", "countered"):
                raise HTTPException(400, "Cannot reject now")
            interest.status = "rejected"

        else:
            raise HTTPException(400, "Invalid action")

    # ---------------- DEAL CREATION (ATOMIC) ----------------
    if interest.status in ("accepted", "agreed"):
        deal.create_deal_from_interest(db, interest)  # caller must commit

        # Mark property unavailable
        property_obj.is_available = False

        # Reject all other interests
        db.query(models.Interest).filter(
            models.Interest.property_id == interest.property_id,
            models.Interest.id != interest.id
        ).update({"status": "rejected"})

    db.commit()
    db.refresh(interest)

    return {"status": interest.status}



@router.get("/buyer", response_model=list[bid.BuyerInterestOut])
def get_buyer_interests(
    db: Session = Depends(get_db),
    current_user = Depends(oauth2.get_current_user),
):
    # 1. Default agent (id = 1)
   

    # 2. Fetch buyer interests
    interests = (
        db.query(models.Interest)
        .filter(models.Interest.buyer_id == current_user.id)
        .order_by(models.Interest.created_at.desc())
        .all()
    )
    
    response = []

    for interest in interests:
        prop = db.query(models.Property).filter(
            models.Property.id == interest.property_id
        ).first()
        agent=agent=db.query(models.Agent).filter(models.Agent.id==interest.agent_id).first()
        if not prop:
            continue  # safety

        # 3. Seller-driven price
        effective_price = pricing.get_effective_price(prop.price, interest)

        # 4. Agent fee on effective price
        agent_fee = pricing.compute_agent_fee(effective_price, agent)

        response.append({
            "interest_id": interest.id,
            "property_id": prop.id,
            "bid_amount": interest.bid_amount,
            "counter_amount": (interest.counter_amount + agent_fee) if interest.counter_amount is not None else None,
            "price_to_pay": effective_price + agent_fee,
            "status": interest.status
        })

    return response





@router.get("/seller", response_model=list[bid.SellerInterestOut])
def get_seller_interests(
    db: Session = Depends(get_db),
    current_user = Depends(oauth2.get_current_user),
):
    

    # 2. Fetch interests on seller's properties
    interests = (
        db.query(models.Interest)
        .join(models.Property, models.Property.id == models.Interest.property_id)
        .filter(models.Property.seller_id == current_user.id)
        .order_by(models.Interest.created_at.desc())
        .all()
    )

    response = []

    for interest in interests:
        prop = interest.property  # already joined
        agent=agent=db.query(models.Agent).filter(models.Agent.id==interest.agent_id).first()
        # 3. Seller-driven price
        effective_price = pricing.get_effective_price(prop.price, interest)

        # 4. Agent fee
        agent_fee = pricing.compute_agent_fee(effective_price, agent)

        response.append({
            "interest_id": interest.id,
            "property_id": prop.id,
            "base_price": prop.price,
            "counter_amount": interest.counter_amount,
            "bid_amount": interest.bid_amount,
            "status": interest.status
        })

    return response
