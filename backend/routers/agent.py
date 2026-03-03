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
        name=new_user.email,
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
    if agent.id!=prop.agent_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="not your job")
    if action not in ("verified", "changes_required"):
        raise HTTPException(status_code=400, detail="Invalid action")

    if action == "verified":
        prop.is_verified = True
        prop.verification_status = "verified"
        prop.verified_by = agent.id  # ← moved here
        prop.remarks = None

    elif action == "changes_required":
        prop.is_verified = False
        prop.verification_status = "changes_required"
        prop.remarks = remarks
        if not remarks:
            raise HTTPException(status_code=400, detail="remarks required when requesting changes")

    db.commit()
    return {"message": f"Property {action}", "property_id": property_id}
   