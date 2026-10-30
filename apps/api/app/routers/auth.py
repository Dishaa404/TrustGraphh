from __future__ import annotations

import secrets
import time
from typing import Any, Literal

from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.store import store

router = APIRouter(prefix="/auth", tags=["auth"])

UserRole = Literal["donor", "receiver", "ngo"]
SESSION_TTL_SECONDS = 12 * 60 * 60


class NonceRequest(BaseModel):
    wallet: str
    role: UserRole = "donor"


class VerifyRequest(BaseModel):
    wallet: str
    signature: str
    nonce: str
    role: UserRole = "donor"


class NgoApplicationRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=120)
    website: str | None = Field(default=None, max_length=200)
    registration_id: str = Field(min_length=2, max_length=120)


def _message(wallet: str, nonce: str, role: UserRole) -> str:
    return (
        "TrustGraph wants you to sign in with your wallet:\n"
        f"{wallet}\n\nRole: {role}\nNonce: {nonce}\n"
        "This signature does not authorize a transaction."
    )


def get_current_session(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sign in with a wallet to continue")

    token = authorization[7:].strip()
    with store.lock:
        session = store.sessions.get(token)
        if session and float(session.get("expires_at", 0)) <= time.time():
            store.sessions.pop(token, None)
            session = None
        if session:
            return {**session, "token": token}

    raise HTTPException(status_code=401, detail="Session is invalid or expired")


def require_roles(*roles: UserRole):
    def authorize(session: dict[str, Any] = Depends(get_current_session)) -> dict[str, Any]:
        if session.get("role") not in roles:
            raise HTTPException(status_code=403, detail="This account role cannot access this feature")
        if session.get("role") == "ngo" and session.get("approval_status") != "approved":
            raise HTTPException(status_code=403, detail="NGO access is pending wallet allow-list approval")
        return session

    return authorize


@router.post("/nonce")
def create_nonce(payload: NonceRequest) -> dict[str, str]:
    wallet = payload.wallet.lower()
    nonce = secrets.token_hex(16)
    with store.lock:
        store.nonces[wallet] = {"nonce": nonce, "role": payload.role}

    return {
        "wallet": wallet,
        "role": payload.role,
        "nonce": nonce,
        "message": _message(wallet, nonce, payload.role),
    }


@router.post("/verify")
def verify(payload: VerifyRequest) -> dict[str, Any]:
    wallet = payload.wallet.lower()

    with store.lock:
        expected = store.nonces.get(wallet)

    if (
        not expected
        or expected.get("role") != payload.role
        or not secrets.compare_digest(expected.get("nonce", ""), payload.nonce)
    ):
        raise HTTPException(status_code=400, detail="Unknown, expired, or mismatched login challenge")

    try:
        recovered = Account.recover_message(
            encode_defunct(text=_message(wallet, payload.nonce, payload.role)),
            signature=payload.signature,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Invalid signature") from exc

    if recovered.lower() != wallet:
        raise HTTPException(status_code=401, detail="Signature does not match wallet")

    settings = get_settings()
    approval_status = (
        "approved" if wallet in settings.ngo_wallet_allowlist else "pending"
    ) if payload.role == "ngo" else "not_applicable"
    now = time.time()
    session_data = {
        "wallet": wallet,
        "role": payload.role,
        "approval_status": approval_status,
        "created_at": now,
        "expires_at": now + SESSION_TTL_SECONDS,
    }
    token = secrets.token_urlsafe(32)
    with store.lock:
        store.nonces.pop(wallet, None)
        store.sessions[token] = session_data

    return {"authenticated": True, "address": recovered, "token": token, **session_data}


@router.get("/me")
def current_user(session: dict[str, Any] = Depends(get_current_session)) -> dict[str, Any]:
    session.pop("token", None)
    session.pop("expires_at", None)
    return {"authenticated": True, **session}


@router.post("/logout")
def logout(
    session: dict[str, Any] = Depends(get_current_session),
    authorization: str | None = Header(default=None),
) -> dict[str, bool]:
    token = authorization[7:].strip() if authorization else ""
    with store.lock:
        store.sessions.pop(token, None)
    return {"authenticated": False}


@router.post("/ngo/application", status_code=201)
def submit_ngo_application(
    payload: NgoApplicationRequest,
    session: dict[str, Any] = Depends(get_current_session),
) -> dict[str, Any]:
    if session.get("role") != "ngo":
        raise HTTPException(status_code=403, detail="Sign in with the NGO role to apply")
    if session.get("approval_status") == "approved":
        raise HTTPException(status_code=409, detail="This NGO wallet is already approved")

    application = {
        "wallet": session["wallet"],
        "organization_name": payload.organization_name,
        "website": payload.website,
        "registration_id": payload.registration_id,
        "status": "pending",
    }
    with store.lock:
        store.ngo_applications[session["wallet"]] = application
    return application
