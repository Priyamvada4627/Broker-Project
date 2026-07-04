from .. import models,utils
from ..schemas import user
from fastapi import FastAPI,Response,status,HTTPException,Depends,APIRouter
from sqlalchemy.orm import Session
from ..database import  get_db
from ..oauth2 import get_current_user
from sqlalchemy.exc import IntegrityError
router=APIRouter(
    prefix="/users",
    tags=['Users']

)


@router.post("/register",status_code=status.HTTP_201_CREATED,response_model=user.UserOut)
def create_user(user: user.UserCreate, db: Session = Depends(get_db)):
    hashed_password = utils.hash(user.password)
    new_user = models.User(**user.dict(exclude={"password"}), password=hashed_password)
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email or phone number is already registered."
        )
    db.refresh(new_user)
    return new_user

@router.get("/me", response_model=user.UserOut)
def get_current_user_profile(
    current_user=Depends(get_current_user)
):
    return current_user