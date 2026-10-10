from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from datetime import datetime
from .database import Base

class Tariff(Base):
    __tablename__="tariffs"
    id=Column(Integer, primary_key=True, index=True)
    title=Column(String, nullable=False)
    price=Column(Integer, nullable=False)

class Payment(Base):
    __tablename__="payments"
    id=Column(Integer, primary_key=True, index=True)
    status=Column(String, nullable=False, default="pending")
    tariff_id=Column(Integer, ForeignKey("tariffs.id"))
    amount=Column(Integer, nullable=False)
    discount=Column(Integer, nullable=False, default=0)
    method=Column(String, nullable=False)
    installment_months=Column(Integer, nullable=True)
    schedule=Column(JSON, nullable=True)
    email=Column(String, nullable=False)
    created_at=Column(DateTime, default=datetime.utcnow, nullable=False)
    idempotency_key=Column(String, unique=True)