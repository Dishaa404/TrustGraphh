from dataclasses import asdict

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.payments.factory import get_payment_provider
from app.store import store

router = APIRouter(prefix="/payments", tags=["payments"])


class PaymentIntentRequest(BaseModel):
    payer_did: str
    amount: float = Field(gt=0)
    asset: str = "USDC"
    provider: str | None = None


class WebhookPayload(BaseModel):
    payment_id: str
    status: str = "confirmed"
    tx_hash: str | None = None


@router.post("/intent", status_code=201)
def create_intent(payload: PaymentIntentRequest) -> dict:
    try:
        provider = get_payment_provider(payload.provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    intent = provider.create_intent(payload.payer_did, payload.amount, payload.asset)
    document = asdict(intent)

    with store.lock:
        store.payments[intent.id] = document

    return document


@router.get("/{payment_id}")
def get_payment(payment_id: str) -> dict:
    with store.lock:
        payment = store.payments.get(payment_id)

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    provider = get_payment_provider(payment["provider"])
    payment["status"] = provider.get_status(payment_id, payment["status"])
    return payment


@router.post("/webhook")
def webhook(payload: WebhookPayload, x_webhook_secret: str | None = Header(default=None)) -> dict:
    settings = get_settings()

    if settings.rodo_webhook_secret and x_webhook_secret != settings.rodo_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    with store.lock:
        payment = store.payments.get(payload.payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        payment["status"] = payload.status
        if payload.tx_hash:
            payment["tx_hash"] = payload.tx_hash

    return payment
