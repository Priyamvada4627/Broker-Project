from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, oauth2
from ..database import get_db
from typing import Optional,Literal,List
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone



router = APIRouter(
    prefix="/deals",
    tags=["Documents"]
)


class DocumentUpload(BaseModel):
    document_type: str
    file_url: str

class DocumentVerify(BaseModel):
    status: str  # verified | rejected
    notes: Optional[str] = None


@router.post("/{deal_id}/documents")
def upload_document(
    deal_id: int,
    document_type: str,
    file_url: str,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    # only buyer or seller can upload
    if current_user.id not in (deal.buyer_id, deal.seller_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check if there's already a pending/verified doc of same type
    existing = db.query(models.DealDocument).filter(
        models.DealDocument.deal_id == deal_id,
        models.DealDocument.document_type == document_type,  # ← payload.document_type → document_type
        models.DealDocument.status.in_(["pending", "verified"])
    ).first()
    if existing:  # ← fixed indentation
        raise HTTPException(400, "Document of this type already exists")

    doc = models.DealDocument(
        deal_id=deal_id,
        document_type=document_type,
        file_url=file_url,
        uploaded_by=current_user.id
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {"message": "Document uploaded", "document_id": doc.id}






@router.patch("/{deal_id}/documents/{document_id}/verify")
def verify_document(
    deal_id: int,
    document_id: int,
    status: str,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.require_agent)
):
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    agent = db.query(models.Agent).filter(models.Agent.user_id == current_user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent profile not found")

    if deal.agent_id != agent.id:
        raise HTTPException(status_code=403, detail="Not your deal")

    if status not in ("verified", "rejected"):
        raise HTTPException(status_code=400, detail="Invalid status")

    doc = db.query(models.DealDocument).filter(
        models.DealDocument.id == document_id,
        models.DealDocument.deal_id == deal_id
    ).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if status == "verified":
        doc.status = "verified"
        doc.verified_by = agent.id
        doc.notes = notes
        doc.reupload_deadline = None  # clear any previous deadline

    elif status == "rejected":
        if not notes:
            raise HTTPException(status_code=400, detail="notes required when rejecting a document")
        doc.status = "rejected"
        doc.verified_by = agent.id
        doc.notes = notes  # rejection reason for buyer/seller
        doc.reupload_deadline = datetime.now(timezone.utc) + timedelta(days=7)
        deal.status = "documents_pending"  # reset deal status

    db.flush()

    # only check if all verified when no rejection happened
    if status == "verified":
        all_docs = db.query(models.DealDocument).filter(
            models.DealDocument.deal_id == deal_id
        ).all()

        if all(d.status == "verified" for d in all_docs):
            deal.status = "documents_verified"

    db.commit()

    return {
        "message": f"Document {status}",
        "document_id": document_id,
        "deal_status": deal.status,
        "notes": doc.notes,
        "reupload_deadline": doc.reupload_deadline
    }




@router.get("/{deal_id}/documents")
def get_deal_documents(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    # only buyer, seller or assigned agent can view
    agent = db.query(models.Agent).filter(models.Agent.user_id == current_user.id).first()
    agent_id = agent.id if agent else None

    if current_user.id not in (deal.buyer_id, deal.seller_id) and deal.agent_id != agent_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    docs = db.query(models.DealDocument).filter(
        models.DealDocument.deal_id == deal_id
    ).all()

    return [
        {
            "document_id": doc.id,
            "document_type": doc.document_type,
            "file_url": doc.file_url,
            "status": doc.status,
            "uploaded_by": doc.uploaded_by,
            "verified_by": doc.verified_by,
            "notes": doc.notes,
            "created_at": doc.created_at
        }
        for doc in docs
    ]