from .database import Base
from sqlalchemy import Column,Integer,String,ForeignKey,Boolean,Float
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.sql.expression import text
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__="users"
    id= Column(Integer,primary_key=True,nullable=False)
    role = Column(String, nullable=False, default="user")

    email=Column(String,nullable=False,unique=True)
    password=Column(String,nullable=False)
    created_at=Column(TIMESTAMP(timezone=True),nullable=False,server_default=text("now()"))
    phone=Column(String,nullable=False,unique=True)
   

class Property(Base):
    __tablename__="properties"
    id=Column(Integer,primary_key=True,nullable=False)
    description=Column(String,nullable=False)
    location=Column(String,nullable=False)
    price=Column(Integer,nullable=False)
    property_type=Column(String,nullable=False)
    purpose=Column(String,nullable=False)
    is_available = Column(Boolean, default=True)
    created_at=Column(TIMESTAMP(timezone=True),nullable=False,server_default=text("now()"))
    seller_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    interests = relationship("Interest", back_populates="property")



class Interest(Base):
    __tablename__ = "interests"

    id = Column(Integer, primary_key=True, nullable=False)
    
    counter_amount = Column(Integer, nullable=True)

    property_id = Column(
        Integer,
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False
    )

    buyer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    bid_amount = Column(Integer, nullable=True)  
    message = Column(String, nullable=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, default=1)
    status = Column(
        String,
        nullable=False,
        default="pending"
    )
    # pending | accepted | rejected | negotiated

    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()")
    )
    property = relationship("Property", back_populates="interests")
    

class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    fee_percent = Column(Float, nullable=False)   # e.g. 2.0
    min_fee = Column(Integer, nullable=True)
    max_fee = Column(Integer, nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()")
    )


class Deal(Base):
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True)

    interest_id = Column(Integer, ForeignKey("interests.id"),unique=True )
    buyer_id = Column(Integer, ForeignKey("users.id"))
    seller_id = Column(Integer, ForeignKey("users.id"))
    property_id = Column(Integer, ForeignKey("properties.id"))
    agent_id = Column(Integer, ForeignKey("agents.id"))

    seller_price = Column(Integer, nullable=False)
    agent_fee = Column(Integer, nullable=False)
    final_price = Column(Integer, nullable=False)
    status = Column(
        String,
        nullable=False,
        default="active"
    )
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()")
    )
