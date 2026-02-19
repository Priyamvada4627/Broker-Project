from fastapi import FastAPI
from .database import engine
from . import models
from .routers import user,auth,property,bid
app = FastAPI()

app.include_router(user.router)
app.include_router(auth.router)
app.include_router(property.router)
app.include_router(bid.router)
models.Base.metadata.create_all(bind=engine)
@app.get("/")
def root():
    return {"message": "Broker project running"}
