from sqlalchemy.orm import Session
from backend import models



def get_platform_agent(db: Session) -> models.Agent:
    agent = db.query(models.Agent).filter(models.Agent.name=='default').first()
    if not agent:
        raise Exception("Platform agent not configured")
    return agent
