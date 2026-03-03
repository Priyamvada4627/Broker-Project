from .. import models,utils
from ..schemas import user
from fastapi import FastAPI,Response,status,HTTPException,Depends,APIRouter
from sqlalchemy.orm import Session
from ..database import  get_db
from ..oauth2 import get_current_user
router=APIRouter(
    prefix="/users",
    tags=['Users']

)
@router.post("/register",status_code=status.HTTP_201_CREATED,response_model=user.UserOut)
def create_user(user: user.UserCreate, db: Session=Depends(get_db)):
    existing=db.query(models.User).filter(models.User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail=f"user with email {user.email} already exists.")
    hashed_password=utils.hash(user.password)
    user.password=hashed_password
    new_user=models.User(**user.dict())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.get("/me", response_model=user.UserOut)
def get_current_user_profile(
    current_user=Depends(get_current_user)
):
    return current_user