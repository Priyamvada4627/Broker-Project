import os
from fastapi import FastAPI
from .database import engine, SessionLocal
from . import models
from .routers import user, auth, property, bid, agent, deal, document, ml
from .services.ml import load_models
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timezone
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# Comma-separated list of allowed frontend origins, e.g.
#   ALLOWED_ORIGINS=https://your-app.vercel.app,http://localhost:3000
# Falls back to "*" (any origin) if not set.
_allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in _allowed_origins.split(",")] if _allowed_origins != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,  # we use Bearer tokens, not cookies, so this can stay False
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(user.router)
app.include_router(auth.router)
app.include_router(property.router)
app.include_router(bid.router)
app.include_router(agent.router)
app.include_router(deal.router)
app.include_router(document.router)
app.include_router(ml.router)

models.Base.metadata.create_all(bind=engine)

# Load ML models into memory on startup
load_models()


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


def retrain_ml_models():
    """
    Retrain ML models every 24 hours by merging Kaggle data
    with live property rows from the DB.
    """
    from .scripts.train_model import train_and_save
    db = SessionLocal()
    try:
        live_properties = db.query(models.Property).filter(
            models.Property.is_verified == True
        ).all()

        extra_rows = []
        for prop in live_properties:
            city = prop.location.city if prop.location else None
            if not city:
                continue
            extra_rows.append({
                "city": city,
                "property_type": prop.property_type.value if hasattr(prop.property_type, 'value') else str(prop.property_type),
                "purpose": prop.purpose.value if hasattr(prop.purpose, 'value') else str(prop.purpose),
                "bedrooms": 2,       # default — bedrooms not in your schema yet
                "area": 1000.0,      # default — area not in your schema yet
                "price": prop.price,
            })

        print(f"[ML Retrain] Adding {len(extra_rows)} live DB rows to training data")
        train_and_save(extra_rows=extra_rows if extra_rows else None)
        load_models()  # reload freshly trained models into memory
        print("[ML Retrain] Models reloaded successfully")
    except Exception as e:
        print(f"[ML Retrain] Error: {e}")
    finally:
        db.close()


scheduler = BackgroundScheduler()
scheduler.add_job(delete_expired_properties, 'interval', hours=24)
scheduler.add_job(delete_expired_documents, 'interval', hours=24)
scheduler.add_job(retrain_ml_models, 'interval', hours=24)
scheduler.start()


# The frontend now lives on its own deployment (e.g. Vercel), so this API
# no longer needs to serve it. This block is kept only for local testing:
# if a "frontend" folder happens to exist next to where you run this from,
# it'll still be served — otherwise it's skipped instead of crashing.
if os.path.isdir("frontend"):
    app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

    @app.get("/")
    def home():
        return FileResponse("frontend/index.html")
else:
    @app.get("/")
    def home():
        return {"status": "ok", "service": "backend API"}