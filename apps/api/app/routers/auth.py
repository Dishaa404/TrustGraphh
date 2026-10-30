import secrets

from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.store import store

router = APIRouter(prefix="/auth", tags=["auth"])


class NonceRequest(BaseModel):
    wallet: str


class VerifyRequest(BaseModel):
    wallet: str
    signature: str
    nonce: str


def _message(wallet: str, nonce: str) -> str:
    return f"TrustGraph wants you to sign in with your wallet:\n{wallet}\n\nNonce: {nonce}"


@router.post("/nonce")
def create_nonce(payload: NonceRequest) -> dict[str, str]:
    nonce = secrets.token_hex(16)
    wallet = payload.wallet.lower()

    with store.lock:
        store.nonces[wallet] = nonce

    return {"wallet": wallet, "nonce": nonce, "message": _message(wallet, nonce)}


@router.post("/verify")
def verify(payload: VerifyRequest) -> dict:
    wallet = payload.wallet.lower()

    with store.lock:
        expected = store.nonces.get(wallet)

    if not expected or not secrets.compare_digest(expected, payload.nonce):
        raise HTTPException(status_code=400, detail="Unknown or expired nonce")

    try:
        recovered = Account.recover_message(
            encode_defunct(text=_message(wallet, payload.nonce)),
            signature=payload.signature,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Invalid signature") from exc

    if recovered.lower() != wallet:
        raise HTTPException(status_code=401, detail="Signature does not match wallet")

    token = secrets.token_urlsafe(32)
    with store.lock:
        store.nonces.pop(wallet, None)
        store.sessions[token] = wallet

    return {"authenticated": True, "address": recovered, "token": token}
