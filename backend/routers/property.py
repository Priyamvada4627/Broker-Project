from fastapi import APIRouter, Response, status, HTTPException, Depends, Query
from ..schemas import Property, bid
from ..database import get_db
from sqlalchemy.orm import Session
from .. import models, oauth2
from typing import List, Optional
from ..services.pricing import compute_agent_fee
from ..services.agent import get_platform_agent
from datetime import datetime, timedelta, timezone
from ..services.ml import predict_price

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
        agent = db.query(models.Agent).filter(models.Agent.id == prop.agent_id).first()
        agent_fee = compute_agent_fee(prop.price, agent)

        response.append({
            "property_id": prop.id,
            "description": prop.description,
            "location": prop.location,
            "price_to_pay": prop.price + agent_fee,
            "is_available": prop.is_available
        })

    return response


@router.get("/my", response_model=list[Property.SellerPropertyOut])
def get_my_properties(
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user),
    is_available: bool | None = None,
):
    query = (
        db.query(models.Property)
        .filter(models.Property.seller_id == current_user.id)
    )

    if is_available is not None:
        query = query.filter(models.Property.is_available == is_available)

    return query.all()


# ── response_model removed because we return extra ml fields ──
@router.get("/{id}")
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

    agent = db.query(models.Agent).filter(models.Agent.id == prop.agent_id).first()
    agent_fee = compute_agent_fee(prop.price, agent)

    ml_estimate = predict_price(
        city=prop.location.city if prop.location else "",
        property_type=prop.property_type.value,
        purpose=prop.purpose.value,
        bedrooms=prop.bedrooms or 2,
        bathrooms=prop.bathrooms or 2,
        area=prop.area or 1000.0
    )

    return {
        "property_id": prop.id,
        "description": prop.description,
        "location": prop.location,
        "price_to_pay": prop.price + agent_fee,
        "is_available": prop.is_available,
        "ml_estimate": ml_estimate.get("predicted_price"),
        "ml_price_range": ml_estimate.get("price_range"),
        "ml_confidence": ml_estimate.get("confidence"),
    }


# ── response_model removed because we return extra ml_price_hint ──
@router.post("/add", status_code=201)
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
        verification_deadline=datetime.now(timezone.utc) + timedelta(days=10),
        
        bedrooms=property.bedrooms,
        bathrooms=property.bathrooms,
        area=property.area
    )
    db.add(new_property)
    db.commit()
    db.refresh(new_property)

    estimate = predict_price(
        city=property.city,
        property_type=property.property_type.value,
        purpose=property.purpose.value,
        bedrooms=property.bedrooms,
        bathrooms=property.bathrooms,
        area=property.area)

    ml_hint = None
    if "predicted_price" in estimate:
        ml_hint = {
            "estimated_fair_price": estimate["predicted_price"],
            "price_range": estimate["price_range"],
            "your_price": property.price,
            "note": "This is an AI estimate. Your listing price may differ."
        }

    return {
        "id": new_property.id,
        "description": new_property.description,
        "location": new_property.location,
        "price": new_property.price,
        "property_type": new_property.property_type,
        "purpose": new_property.purpose,
        "is_available": new_property.is_available,
        "is_verified": new_property.is_verified,
        "verification_status": new_property.verification_status,
        "remarks": new_property.remarks,
        "interests": [],
        "ml_price_hint": ml_hint
    }


@router.patch("/{property_id}")
def update_property(
    property_id: int,
    payload: Property.PropertyUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
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

    city = prop.location.city if prop.location else None
    prop.agent_id = get_platform_agent(db, city=city).id

    prop.is_verified = False
    prop.verification_status = "pending"
    prop.is_modified = True
    prop.remarks = None
    prop.verification_deadline = datetime.now(timezone.utc) + timedelta(days=5)

    db.commit()
    return {"message": "Property updated, resubmitted for verification"}


@router.delete("/{property_id}", status_code=204)
def delete_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    prop = db.query(models.Property).filter(models.Property.id == property_id).first()

    if not prop:
        raise HTTPException(404, "Property not found")
    if prop.seller_id != current_user.id:
        raise HTTPException(403, "Not your property")
    if prop.is_verified:
        raise HTTPException(400, "Cannot delete a verified property — contact your agent")

    existing_deal = db.query(models.Deal).filter(
        models.Deal.property_id == property_id
    ).first()
    if existing_deal:
        raise HTTPException(400, "Cannot delete a property that has an active deal")

    db.delete(prop)
    db.commit()