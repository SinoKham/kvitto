from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import List, Optional, Literal
from datetime import datetime

class TariffResponse(BaseModel):
    id: int
    title: str
    price: int

    model_config = ConfigDict(from_attributes=True)

class PaymentCreate(BaseModel):
    tariff_id: int
    email: EmailStr
    method: Literal["card", "sbp", "installment"]
    installment_months: Optional[int] =None
    promo_code: Optional[str]= None

class PaymentResponse(BaseModel):
    id: int
    status: str
    tariff_id: int
    amount: int
    discount: int
    schedule: Optional[List[int]]
    email: str
    method: str
    installment_months: Optional[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WebhookPayload(BaseModel):
    payment_id: int
    status: str