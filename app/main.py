from fastapi import FastAPI, Depends, HTTPException, Header, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from . import models, schemas
from .database import engine, get_db, SessionLocal

ALLOWED_TRANSITIONS = {
    "pending": ["succeeded", "failed"],
    "succeeded": ["refunded"],
    "failed": [],
    "refunded": [],
}

app=FastAPI()

@app.on_event("startup")
def seed_tariffs():
    db=SessionLocal()
    try:
        if db.query(models.Tariff).count()==0:
            db.add_all([models.Tariff(title="basic", price=990000), 
                        models.Tariff(title="standard", price=1990000), 
                        models.Tariff(title="premium", price=2990000)])
            db.commit()
    finally:
        db.close()

@app.get("/tariffs", response_model=List[schemas.TariffResponse])
def get_tariffs(db: Session=Depends(get_db)):
    return db.query(models.Tariff).all()

@app.post("/payments", response_model=schemas.PaymentResponse, status_code=201)
def create_payment(
    payment_data:schemas.PaymentCreate,
    response: Response,
    db: Session=Depends(get_db),
    idempotency_key: Optional[str]=Header(None)
):
    if idempotency_key:
        existing=db.query(models.Payment).filter(models.Payment.idempotency_key==idempotency_key).first()
        if existing:
            response.status_code=200
            return existing

    tariff=db.query(models.Tariff).filter(models.Tariff.id==payment_data.tariff_id).first()
    if not tariff:
        raise HTTPException(status_code=422, detail="Tariff not found")

    amount=tariff.price
    discount=0
    if payment_data.promo_code:
        if payment_data.promo_code.lower()!="kvitto10":
            raise HTTPException(status_code=422, detail="Unknown promo code")
        discount=amount//10
        amount-=discount

    schedule=None
    installment_months=None
    if payment_data.method=="installment":
        installment_months=payment_data.installment_months
        if installment_months not in [3, 6, 12]:
            raise HTTPException(status_code=422, detail="Invalid installment months")
        base=amount//installment_months 
        remainder=amount%installment_months
        schedule=[base+1]*remainder+[base]*(installment_months-remainder) 

    new_payment=models.Payment(
        status="pending",
        tariff_id=tariff.id,
        amount=amount,
        discount=discount,
        method=payment_data.method,
        installment_months=installment_months,
        schedule=schedule,
        email=payment_data.email,
        idempotency_key=idempotency_key
    )
    db.add(new_payment)
    try:
        db.commit()
        db.refresh(new_payment)
        return new_payment
    except IntegrityError:
        db.rollback()
        existing = db.query(models.Payment).filter(models.Payment.idempotency_key == idempotency_key).first()
        if existing:
            response.status_code=200
            return existing
        raise HTTPException(status_code=500, detail="Unexpected error")

@app.get("/payments/{payment_id}", response_model=schemas.PaymentResponse)
def get_payment(payment_id: int, db: Session=Depends(get_db)):
    payment=db.query(models.Payment).filter(models.Payment.id==payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment

@app.post("/webhooks/bank")
def bank_webhook(
    payload: schemas.WebhookPayload,
    db: Session = Depends(get_db)
):
    payment=db.query(models.Payment).filter(models.Payment.id == payload.payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    allowed=ALLOWED_TRANSITIONS.get(payment.status, [])
    if payload.status not in allowed:
        return JSONResponse(
            status_code=409,
            content={"error":"invalid_transition"}
        )
    payment.status=payload.status
    db.commit()
    db.refresh(payment)
    return {"result":"ok"}