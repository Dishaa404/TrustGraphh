from dataclasses import asdict

from fastapi import APIRouter, Header, HTTPException
from eth_utils import keccak
from pydantic import BaseModel, Field

from app.config import get_settings
from app.payments.base import PaymentProviderError
from app.payments.factory import get_payment_provider
from app.store import store
from app.tigergraph import graph_client

router = APIRouter(prefix="/payments", tags=["payments"])


class PaymentIntentRequest(BaseModel):
    payer_did: str
    payer_wallet: str | None = Field(default=None, pattern=r"^0x[0-9a-fA-F]{40}$")
    amount: float = Field(gt=0)
    asset: str = "XMR"
    provider: str | None = None


class WebhookPayload(BaseModel):
    payment_id: str
    status: str = "confirmed"
    tx_hash: str | None = None


@router.post("/intent", status_code=201)
def create_intent(payload: PaymentIntentRequest) -> dict:
    if payload.payer_wallet:
        expected_did = "did:trustgraph:0x" + keccak(text=payload.payer_wallet.lower()).hex()
        if payload.payer_did != expected_did:
            raise HTTPException(status_code=400, detail="payer_did does not match payer_wallet")
    try:
        provider = get_payment_provider(payload.provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        intent = provider.create_intent(payload.payer_did, payload.amount, payload.asset)
    except PaymentProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    document = asdict(intent)
    document["payer_wallet"] = payload.payer_wallet

    with store.lock:
        store.payments[intent.id] = document
    graph_client.upsert_payment(document)

    return document


@router.get("/{payment_id}")
def get_payment(payment_id: str) -> dict:
    with store.lock:
        payment = store.payments.get(payment_id)

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    provider = get_payment_provider(payment["provider"])
    try:
        payment["status"] = provider.get_status(
            payment_id, payment["status"], payment.get("provider_data")
        )
    except PaymentProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    with store.lock:
        store.payments[payment_id]["status"] = payment["status"]
    graph_client.upsert_payment(payment)
    return payment


@router.post("/webhook")
def webhook(payload: WebhookPayload, x_webhook_secret: str | None = Header(default=None)) -> dict:
    settings = get_settings()

    if not settings.rodo_webhook_secret:
        raise HTTPException(status_code=503, detail="Payment webhooks are not configured")
    if x_webhook_secret != settings.rodo_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    with store.lock:
        payment = store.payments.get(payload.payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        if payment["provider"] != "rodo":
            raise HTTPException(status_code=400, detail="Cake Wallet payment status is checked through wallet RPC")
        if payload.status not in {"pending", "confirming", "confirmed", "failed", "expired"}:
            raise HTTPException(status_code=400, detail="Unsupported payment status")

        payment["status"] = payload.status
        if payload.tx_hash:
            payment["tx_hash"] = payload.tx_hash

    graph_client.upsert_payment(payment)
    return payment
