from datetime import datetime, timezone
from hashlib import sha256
from time import time_ns

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.routers.auth import require_roles
from app.store import store
from app.tigergraph import graph_client

router = APIRouter(prefix="/credentials", tags=["credentials"])


class CredentialCreate(BaseModel):
    subject_did: str
    issuer: str
    credential_type: str
    content_hash: str
    cid: str
    expires_at: str | None = None


class RevokeRequest(BaseModel):
    reason: str = ""


@router.post("", status_code=201)
def issue(payload: CredentialCreate, session: dict = Depends(require_roles("ngo"))) -> dict:
    if payload.issuer.lower() != session["wallet"]:
        raise HTTPException(status_code=403, detail="NGOs can only issue credentials from their signed-in wallet")
    subject = store.persons.get(payload.subject_did)
    if not subject or subject.get("status") != "active":
        raise HTTPException(status_code=409, detail="Credentials can only be issued to an active registered person")
    credential_id = "cred:" + sha256(
        f"{payload.subject_did}:{payload.content_hash}:{payload.issuer}:{time_ns()}".encode()
    ).hexdigest()[:32]

    credential = {
        "id": credential_id,
        "status": "valid",
        "issued_at": datetime.now(timezone.utc).isoformat(),
        **payload.model_dump(),
    }

    with store.lock:
        store.credentials[credential_id] = credential

    graph_client.upsert_credential(credential)

    return credential


@router.get("/{credential_id}")
def get_credential(credential_id: str) -> dict:
    with store.lock:
        credential = store.credentials.get(credential_id)

    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    return credential


@router.post("/{credential_id}/revoke")
def revoke(
    credential_id: str,
    payload: RevokeRequest,
    session: dict = Depends(require_roles("ngo")),
) -> dict:
    def apply_revocation(credential: dict) -> dict:
        if credential["issuer"].lower() != session["wallet"]:
            raise HTTPException(status_code=403, detail="NGOs can only revoke credentials issued by their wallet")
        credential["status"] = "revoked"
        credential["revocation_reason"] = payload.reason
        credential["revoked_at"] = datetime.now(timezone.utc).isoformat()
        return credential

    with store.lock:
        credential = store.credentials.mutate(credential_id, apply_revocation)
        if not credential:
            raise HTTPException(status_code=404, detail="Credential not found")

    graph_client.upsert_credential(credential)

    return credential
