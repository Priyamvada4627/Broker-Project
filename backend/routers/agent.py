from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import models, oauth2, utils
from ..database import get_db
from ..schemas import agent

router = APIRouter(
    prefix="/agents",
    tags=["Agents"]
)


@router.post("/register", status_code=201)
def register_agent(
    agent: agent.Agent_In,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.require_agent)
):
    existing = db.query(models.User).filter(models.User.email == agent.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="User with this email already exists")

    new_user = models.User(
        email=agent.email,
        password=utils.hash(agent.password),
        phone=agent.phone,
        role="agent"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    new_agent = models.Agent(
        user_id=new_user.id,
        name=agent.name,
        fee_percent=agent.fee_percent,
        min_fee=agent.min_fee,
        max_fee=agent.max_fee
    )
    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)

    return {"message": "Agent created", "agent_id": new_agent.id, "user_id": new_user.id}


@router.patch("/verify/property/{property_id}")
def verify_property(
    property_id: int,
    action: str,          # "verified" | "changes_required"
    remarks: str = None,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.require_agent)
):
    prop = db.query(models.Property).filter(models.Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    agent = db.query(models.Agent).filter(models.Agent.user_id == current_user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent profile not found")
    if agent.id != prop.agent_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your job")
    if action not in ("verified", "changes_required"):
        raise HTTPException(status_code=400, detail="Invalid action")

    if action == "verified":
        prop.is_verified = True
        prop.verification_status = "verified"
        prop.verified_by = agent.id
        prop.remarks = None

    elif action == "changes_required":
        prop.is_verified = False
        prop.verification_status = "changes_required"
        if not remarks:
            raise HTTPException(status_code=400, detail="remarks required when requesting changes")
        prop.remarks = remarks

    db.commit()
    return {"message": f"Property {action}", "property_id": property_id}


@router.get("/dashboard")
def agent_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.require_agent)
):
    agent = db.query(models.Agent).filter(models.Agent.user_id == current_user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent profile not found")

    # Properties assigned to this agent
    properties = db.query(models.Property).filter(
        models.Property.agent_id == agent.id
    ).all()

    assigned_properties = [
        {
            "property_id": p.id,
            "description": p.description,
            "city": p.location.city if p.location else None,
            "price": p.price,
            "verification_status": p.verification_status,
            "is_verified": p.is_verified,
            "is_modified": p.is_modified,
            "remarks": p.remarks,
            "verification_deadline": p.verification_deadline,
        }
        for p in properties
    ]

    # Active deals assigned to this agent
    active_deals = db.query(models.Deal).filter(
        models.Deal.agent_id == agent.id,
        models.Deal.status.notin_(["completed", "cancelled"])
    ).all()

    deals_out = [
        {
            "deal_id": d.id,
            "property_id": d.property_id,
            "buyer_id": d.buyer_id,
            "seller_id": d.seller_id,
            "final_price": d.final_price,
            "status": d.status,
            "created_at": d.created_at,
        }
        for d in active_deals
    ]

    # Pending documents across all agent's deals
    pending_docs = (
        db.query(models.DealDocument)
        .join(models.Deal, models.Deal.id == models.DealDocument.deal_id)
        .filter(
            models.Deal.agent_id == agent.id,
            models.DealDocument.status == "pending"
        )
        .all()
    )

    docs_out = [
        {
            "document_id": doc.id,
            "deal_id": doc.deal_id,
            "document_type": doc.document_type,
            "uploaded_by": doc.uploaded_by,
            "created_at": doc.created_at,
        }
        for doc in pending_docs
    ]

    return {
        "agent_id": agent.id,
        "name": agent.name,
        "city": agent.city,
        "summary": {
            "total_assigned_properties": len(assigned_properties),
            "pending_verification": sum(1 for p in assigned_properties if p["verification_status"] == "pending"),
            "active_deals": len(deals_out),
            "pending_documents": len(docs_out),
        },
        "properties": assigned_properties,
        "active_deals": deals_out,
        "pending_documents": docs_out,
    }