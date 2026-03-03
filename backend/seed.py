# seed.py
from backend.database import SessionLocal
from backend import models
from backend.utils import hash

db = SessionLocal()

user = models.User(
    email="agent@platform.com",
    password=hash("securepassword"),
    phone="9999999999",
    role="agent"
)
db.add(user)
db.commit()
db.refresh(user)

agent = models.Agent(
    user_id=user.id, 
    name="default",
    fee_percent=2.0,
    min_fee=1000,
    max_fee=50000
)
db.add(agent)
db.commit()