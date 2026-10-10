import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app import models

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine=create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread":False},
    poolclass=StaticPool,  
)
TestingSessionLocal=sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db=TestingSessionLocal()

    db.add_all([
        models.Tariff(title="basic", price=990000),
        models.Tariff(title="standard", price=1990000),
        models.Tariff(title="premium", price=2990000),
    ])
    db.commit()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db]=override_get_db
    app.router.on_startup.clear()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()