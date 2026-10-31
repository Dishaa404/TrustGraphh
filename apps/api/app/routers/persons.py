from datetime import datetime, timezone
from hashlib import sha256

from fastapi import APIRouter, Depends, HTTPException
from eth_utils import keccak
from pydantic import BaseModel, Field

from app.store import store
from app.routers.auth import require_roles
from app.tigergraph import graph_client

router = APIRouter(prefix="/persons", tags=["persons"])


class PersonCreate(BaseModel):
    wallet: str = Field(min_length=4)
    did: str | None = None
    country: str | None = None
    biometric_hash: str | None = None


class VouchCreate(BaseModel):
    voucher_did: str
    weight: float = 1.0


@router.post("", status_code=201)
def create_person(payload: PersonCreate, session: dict = Depends(require_roles("receiver"))) -> dict:
    if payload.wallet.lower() != session["wallet"]:
        raise HTTPException(status_code=403, detail="Receivers can only register their signed-in wallet")
    did = payload.did or "did:trustgraph:0x" + keccak(text=payload.wallet.lower()).hex()
    country_hash = sha256(payload.country.encode()).hexdigest() if payload.country else None

    with store.lock:
        person = {
            "did": did,
            "wallet": payload.wallet,
            "status": "pending",
            "country_hash": country_hash,
            "biometric_hash": payload.biometric_hash,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "vouches": [],
        }
        if not store.persons.put_if_absent(did, person):
            raise HTTPException(status_code=409, detail="Person already exists")

    graph_client.upsert_person(
        {
            **person,
            "country_hash": country_hash or "",
            "biometric_hash": payload.biometric_hash or "",
        }
    )
    return person


@router.get("/{did}")
def get_person(did: str) -> dict:
    with store.lock:
        person = store.persons.get(did)

    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    return person


@router.get("/{did}/trust")
def get_trust(did: str) -> dict:
    if not graph_client.configured:
        raise HTTPException(status_code=503, detail="TigerGraph is not configured")
    return graph_client.trust_score(did)


@router.post("/{did}/vouch", status_code=409)
def vouch(
    did: str,
    payload: VouchCreate,
    session: dict = Depends(require_roles("receiver", "ngo")),
) -> dict:
    raise HTTPException(
        status_code=409,
        detail="Vouches must be submitted to the Base Sepolia registry; the API indexes the confirmed contract event.",
    )
