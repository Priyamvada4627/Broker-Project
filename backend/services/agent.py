from sqlalchemy.orm import Session
from backend import models

from sqlalchemy.orm import Session
from sqlalchemy import func
from backend import models

def get_platform_agent(db: Session, city: str = None) -> models.Agent:
    if city:
        # find agent in this city with fewest active deals
        agent = (
            db.query(models.Agent)
            .filter(models.Agent.city.ilike(f"%{city}%"))
            .outerjoin(models.Deal, models.Deal.agent_id == models.Agent.id)
            .group_by(models.Agent.id)
            .order_by(func.count(models.Deal.id).asc())
            .first()
        )
        if agent:
            return agent

    # fallback to default
    agent = db.query(models.Agent).filter(models.Agent.name == 'default').first()
    if not agent:
        raise Exception("Platform agent not configured")
    return agent