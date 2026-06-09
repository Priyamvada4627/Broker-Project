from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from .. import models, oauth2
from ..database import get_db
from ..services.cloudinary_service import upload_verification_file, delete_verification_file
from typing import Optional
from datetime import datetime, timedelta, timezone
import os

router = APIRouter(
    prefix="/deals",
    tags=["Documents"]
)

# 10 MB limit for uploaded verification files
MAX_FILE_SIZE = 10 * 1024 * 1024

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}


@router.post("/{deal_id}/documents", status_code=201)
async def upload_document(
    deal_id: int,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    if current_user.id not in (deal.buyer_id, deal.seller_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    # Validate MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file.content_type}'. Allowed: PDF, JPEG, PNG, WEBP."
        )

    # Check for existing pending/verified doc of same type
    existing = db.query(models.DealDocument).filter(
        models.DealDocument.deal_id == deal_id,
        models.DealDocument.document_type == document_type,
        models.DealDocument.status.in_(["pending", "verified"])
    ).first()
    if existing:
        raise HTTPException(400, "Document of this type already exists")

    # Read file and enforce size limit
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10 MB.")

    # Build a clean filename: <document_type>_<user_id>.<ext>
    ext = os.path.splitext(file.filename or "")[1] or ".bin"
    clean_filename = f"{document_type}_{current_user.id}{ext}"

    # Upload to Cloudinary
    try:
        upload_result = upload_verification_file(file_bytes, clean_filename, deal_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"File upload failed: {str(e)}")

    doc = models.DealDocument(
        deal_id=deal_id,
        document_type=document_type,
        file_url=upload_result["url"],
        cloudinary_public_id=upload_result["public_id"],
        uploaded_by=current_user.id
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {
        "message": "Document uploaded",
        "document_id": doc.id,
        "file_url": doc.file_url
    }


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

    doc = db.query(models.DealDocument).filter(
        models.DealDocument.id == document_id,
        models.DealDocument.deal_id == deal_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if status not in ["verified", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    if status == "verified":
        doc.status = "verified"
        doc.verified_by = agent.id
        doc.notes = notes
        doc.reupload_deadline = None
    else:
        if not notes:
            raise HTTPException(
                status_code=400,
                detail="notes required when rejecting a document"
            )
        doc.status = "rejected"
        doc.verified_by = agent.id
        doc.notes = notes
        doc.reupload_deadline = datetime.now(timezone.utc) + timedelta(days=7)
        deal.status = "documents_pending"

    db.flush()

    if status == "verified":
        docs = db.query(models.DealDocument).filter(
            models.DealDocument.deal_id == deal_id
        ).all()
        latest_docs = {}
        for d in docs:
            latest_docs[d.document_type] = d

        if all(d.status == "verified" for d in latest_docs.values()):
            deal.status = "documents_verified"

    db.commit()
    db.refresh(deal)

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
