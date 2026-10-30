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
    status: str = "pending"


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
        if did in store.persons:
            raise HTTPException(status_code=409, detail="Person already exists")

        person = {
            "did": did,
            "wallet": payload.wallet,
            "status": payload.status,
            "country_hash": country_hash,
            "biometric_hash": payload.biometric_hash,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "vouches": [],
        }
        store.persons[did] = person

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
    return graph_client.trust_score(did)


@router.post("/{did}/vouch", status_code=201)
def vouch(
    did: str,
    payload: VouchCreate,
    session: dict = Depends(require_roles("receiver", "ngo")),
) -> dict:
    with store.lock:
        target = store.persons.get(did)
        voucher = store.persons.get(payload.voucher_did)

        if not target or not voucher:
            raise HTTPException(status_code=404, detail="Person or voucher not found")
        if voucher["wallet"].lower() != session["wallet"]:
            raise HTTPException(status_code=403, detail="A wallet can only vouch as its own registered person")
        if target["did"] == voucher["did"]:
            raise HTTPException(status_code=400, detail="Cannot vouch for yourself")
        if payload.voucher_did in target["vouches"]:
            raise HTTPException(status_code=409, detail="Already vouched")

        target["vouches"].append(payload.voucher_did)
        if len(target["vouches"]) >= 3 and target["status"] == "pending":
            target["status"] = "active"

        result = {"target": did, "voucher": payload.voucher_did, "vouches": len(target["vouches"])}

    graph_client.upsert_vouch(payload.voucher_did, did, payload.weight)
    return result
