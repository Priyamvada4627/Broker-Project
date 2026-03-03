from fastapi import FastAPI
from .database import engine, SessionLocal
from . import models
from .routers import user, auth, property, bid, agent, deal, document
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timezone

app = FastAPI()

app.include_router(user.router)
app.include_router(auth.router)
app.include_router(property.router)
app.include_router(bid.router)
app.include_router(agent.router)
app.include_router(deal.router)
app.include_router(document.router)

models.Base.metadata.create_all(bind=engine)


def delete_expired_properties():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        expired = db.query(models.Property).filter(
            models.Property.is_verified == False,
            models.Property.verification_deadline < now
        ).all()
        for prop in expired:
            db.delete(prop)
        db.commit()
        print(f"Deleted {len(expired)} expired properties")
    except Exception as e:
        print(f"Scheduler error: {e}")
        db.rollback()
    finally:
        db.close()


def delete_expired_documents():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        expired_docs = db.query(models.DealDocument).filter(
            models.DealDocument.status == "rejected",
            models.DealDocument.reupload_deadline < now
        ).all()
        for doc in expired_docs:
            deal = db.query(models.Deal).filter(models.Deal.id == doc.deal_id).first()
            if deal:
                deal.status = "cancelled"
        db.commit()
        print(f"Cancelled {len(expired_docs)} deals with expired document reupload deadlines")
    except Exception as e:
        print(f"Scheduler error: {e}")
        db.rollback()
    finally:
        db.close()


scheduler = BackgroundScheduler()
scheduler.add_job(delete_expired_properties, 'interval', hours=24)
scheduler.add_job(delete_expired_documents, 'interval', hours=24)
scheduler.start()


@app.get("/")
def root():
    return {"message": "Broker project running"}