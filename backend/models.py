from .database import Base
from sqlalchemy import Column,Integer,String,ForeignKey,Boolean,Float,UniqueConstraint,Enum
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.sql.expression import text
from sqlalchemy.orm import relationship
import enum

class PropertyPurpose(str, enum.Enum):
    buy = "buy"
    rent = "rent"

class PropertyType(str, enum.Enum):
    apartment = "apartment"
    house = "house"
    flat = "flat"
    plot = "plot"
    commercial = "commercial"

class User(Base):
    __tablename__="users"
    id= Column(Integer,primary_key=True,nullable=False)
    role = Column(String, nullable=False, default="customer")

    email=Column(String,nullable=False,unique=True)
    password=Column(String,nullable=False)
    created_at=Column(TIMESTAMP(timezone=True),nullable=False,server_default=text("now()"))
    phone=Column(String,nullable=False,unique=True)


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    pincode = Column(String, nullable=False)


class Property(Base):
    __tablename__ = "properties"
    
    id = Column(Integer, primary_key=True, nullable=False)
    description = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    purpose = Column(Enum(PropertyPurpose), nullable=False)
    property_type = Column(Enum(PropertyType), nullable=False)
    is_available = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    seller_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    verification_deadline = Column(TIMESTAMP(timezone=True), nullable=True)
    is_modified = Column(Boolean, default=False)
    # models.py
    remarks = Column(String, nullable=True)  
    verification_status = Column(String, default="pending") 
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    agent_rel = relationship("Agent", foreign_keys=[agent_id])
    
    location = relationship("Location")
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
    __table_args__ = (
        UniqueConstraint('buyer_id', 'property_id', name='uq_buyer_property'),
    )
    agent = relationship("Agent")
class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    name = Column(String, nullable=False)
    fee_percent = Column(Float, nullable=False)
    city = Column(String, nullable=True)
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
    property_id = Column(Integer, ForeignKey("properties.id"),unique=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))

    seller_price = Column(Integer, nullable=False)
    agent_fee = Column(Integer, nullable=False)
    final_price = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="created")
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()")
    )


class DealDocument(Base):
    __tablename__ = "deal_documents"

    id = Column(Integer, primary_key=True)
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False)
    document_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_url = Column(String, nullable=False)
    verified_by = Column(Integer, ForeignKey("agents.id"), nullable=True)
    notes = Column(String, nullable=True)
    reupload_deadline = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()")
    )