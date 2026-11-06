# tests/conftest.py
import os
os.environ["TESTING"] = "True"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.database import Base, get_db
from backend import models, utils, oauth2

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Fresh tables before each test and drop after."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """FastAPI TestClient that overrides get_db with in-memory DB."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function", autouse=True)
def default_platform_agent(db):
    """Ensures fallback platform agent always exists in test DB."""
    agent_user = models.User(
        email="default_agent@platform.com",
        password=utils.hash("defaultpass"),
        phone="0000000000",
        role="agent"
    )
    db.add(agent_user)
    db.commit()
    db.refresh(agent_user)

    default_agent = models.Agent(
        user_id=agent_user.id,
        name="default",
        city="Platform",
        fee_percent=2.0,
        min_fee=1000,
        max_fee=50000
    )
    db.add(default_agent)
    db.commit()
    db.refresh(default_agent)
    return default_agent


@pytest.fixture(scope="function")
def test_user(db):
    """Seller user."""
    user = models.User(
        email="seller@example.com",
        password=utils.hash("password123"),
        phone="9876543210",
        role="customer"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_user2(db):
    """Buyer 1 user."""
    user = models.User(
        email="buyer1@example.com",
        password=utils.hash("password123"),
        phone="9876543211",
        role="customer"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_user3(db):
    """Buyer 2 user (competing bidder)."""
    user = models.User(
        email="buyer2@example.com",
        password=utils.hash("password123"),
        phone="9876543212",
        role="customer"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_agent_user(db):
    """City Agent user."""
    user = models.User(
        email="agent_delhi@example.com",
        password=utils.hash("agentpassword"),
        phone="9123456789",
        role="agent"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    agent = models.Agent(
        user_id=user.id,
        name="Delhi Agent",
        city="Delhi",
        fee_percent=2.0,
        min_fee=1000,
        max_fee=50000
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@pytest.fixture(scope="function")
def user_token(test_user):
    return oauth2.create_access_token(data={"user_id": test_user.id})


@pytest.fixture(scope="function")
def user2_token(test_user2):
    return oauth2.create_access_token(data={"user_id": test_user2.id})


@pytest.fixture(scope="function")
def user3_token(test_user3):
    return oauth2.create_access_token(data={"user_id": test_user3.id})


@pytest.fixture(scope="function")
def agent_token(test_agent_user):
    return oauth2.create_access_token(data={"user_id": test_agent_user.user_id})


@pytest.fixture(scope="function")
def auth_headers(user_token):
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture(scope="function")
def auth_headers_buyer(user2_token):
    return {"Authorization": f"Bearer {user2_token}"}


@pytest.fixture(scope="function")
def auth_headers_buyer2(user3_token):
    return {"Authorization": f"Bearer {user3_token}"}


@pytest.fixture(scope="function")
def auth_headers_agent(agent_token):
    return {"Authorization": f"Bearer {agent_token}"}
