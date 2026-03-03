from fastapi import APIRouter,Response,status,HTTPException,Depends,Query
from ..schemas import Property,bid
from ..database import get_db
from sqlalchemy.orm import Session
from .. import models,oauth2
from typing import List,Optional
from ..services.pricing import compute_agent_fee
from ..services.agent import get_platform_agent
from datetime import datetime, timedelta, timezone

router = APIRouter(
    prefix="/properties",
    tags=["Properties"]
)

@router.get("/all", response_model=List[Property.BuyerPropertyOut])
def get_all_property(
    city: Optional[str] = None,
    purpose: Optional[str] = None,
    property_type: Optional[str] = None,
    price_min: Optional[int] = Query(None, ge=0),
    price_max: Optional[int] = Query(None, ge=0),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: int = Depends(oauth2.get_current_user)
):
    # Fetch default agent ONCE
    

    query = db.query(models.Property)

    if city:
        query = query.join(models.Location, models.Location.id == models.Property.location_id).filter(models.Location.city.ilike(f"%{city}%"))

    if purpose:
        query = query.filter(models.Property.purpose == purpose)

    if property_type:
        query = query.filter(models.Property.property_type == property_type)

    if price_min is not None:
        query = query.filter(models.Property.price >= price_min)

    if price_max is not None:
        query = query.filter(models.Property.price <= price_max)

    properties = query.offset(offset).limit(limit).all()

    response = []

    for prop in properties:
        agent=db.query(models.Agent).filter(models.Agent.id==prop.agent_id).first()
        agent_fee = compute_agent_fee(prop.price, agent)

        response.append({
            "property_id": prop.id, 
            "description":prop.description,
            "price_to_pay": prop.price + agent_fee,
            "is_available": prop.is_available
        })

    return response




@router.get("/my", response_model=list[Property.SellerPropertyOut])
def get_my_properties(
    db: Session = Depends(get_db),
    current_user = Depends(oauth2.get_current_user),
    is_available: bool | None = None,
):
    query = (
        db.query(models.Property)
        .filter(models.Property.seller_id == current_user.id)
    )

    if is_available is not None:
        query = query.filter(models.Property.is_available == is_available)

    return query.all()




@router.get("/{id}", response_model=Property.BuyerPropertyOut)
def get_property(
    id: int,
    db: Session = Depends(get_db),
    current_user: int = Depends(oauth2.get_current_user)
):
    prop = db.query(models.Property).filter(models.Property.id == id).first()

    if not prop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"property with id: {id} was not found"
        )

    # Fetch default agent
    agent=db.query(models.Agent).filter(models.Agent.id==prop.agent_id).first()

    agent_fee = compute_agent_fee(prop.price, agent)

    return {
        "property_id": prop.id,
        "description":prop.description,
        "price_to_pay": prop.price + agent_fee,
        "is_available": prop.is_available
    }
from datetime import datetime, timedelta, timezone

@router.post("/add", status_code=201, response_model=Property.SellerPropertyOut)
def add_property(
    property: Property.PropertyIn,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    location = models.Location(
        city=property.city,
        state=property.state,
        pincode=property.pincode
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    
    new_property = models.Property(
        seller_id=current_user.id,
        location_id=location.id,
        description=property.description,
        price=property.price,
        property_type=property.property_type,
        purpose=property.purpose,
        agent_id=get_platform_agent(db, city=location.city).id,
        is_available=property.is_available,
        is_modified=False,                                            
        verification_deadline=datetime.now(timezone.utc) + timedelta(days=10)  
    )
    db.add(new_property)
    db.commit()
    db.refresh(new_property)

    return new_property

@router.patch("/{property_id}")
def update_property(
    property_id: int,
    payload: Property.PropertyUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(oauth2.get_current_user)
):
    prop = db.query(models.Property).filter(models.Property.id == property_id).first()
    
    if not prop:
        raise HTTPException(404, "Property not found")
    if prop.seller_id != current_user.id:
        raise HTTPException(403, "Not your property")
    if prop.is_verified:
        raise HTTPException(400, "Cannot modify a verified property")

    if payload.price is not None: prop.price = payload.price
    if payload.description is not None: prop.description = payload.description
    if payload.property_type is not None: prop.property_type = payload.property_type
    if payload.purpose is not None: prop.purpose = payload.purpose
    prop.is_verified = False
    prop.is_modified = True
    prop.verification_deadline = datetime.now(timezone.utc) + timedelta(days=5)

    db.commit()
    return {"message": "Property updated, resubmitted for verification"}