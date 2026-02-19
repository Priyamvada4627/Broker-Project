from fastapi import APIRouter,Response,status,HTTPException,Depends,Query
from ..schemas import Property,bid
from ..database import get_db
from sqlalchemy.orm import Session
from .. import models,oauth2
from typing import List,Optional
from ..services.pricing import compute_agent_fee
from ..services.agent import get_platform_agent


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
    agent = get_platform_agent(db)

    query = db.query(models.Property)

    if city:
        query = query.filter(models.Property.location.ilike(f"%{city}%"))

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
    agent = get_platform_agent(db)

    agent_fee = compute_agent_fee(prop.price, agent)

    return {
        "property_id": prop.id,
        "description":prop.description,
        "price_to_pay": prop.price + agent_fee,
        "is_available": prop.is_available
    }


@router.post("/add",status_code=status.HTTP_201_CREATED,response_model=Property.SellerPropertyOut)   #schema will change
def add_property(property:Property.PropertyIn, db: Session=Depends(get_db),current_user:int =Depends(oauth2.get_current_user) ):
    new_property=models.Property(seller_id=current_user.id,**property.dict())
    db.add(new_property)
    db.commit()
    db.refresh(new_property)
    agent = get_platform_agent(db)

    agent_fee = compute_agent_fee(new_property.price, agent)

    return {
        "id": new_property.id,
        "location":new_property.location,
        "price": new_property.price,
        "description":new_property.description,
        "property_type":new_property.property_type,
        "purpose":new_property.purpose,
        "is_available": new_property.is_available
    }









