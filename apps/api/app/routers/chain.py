from __future__ import annotations

from datetime import datetime, timezone

import httpx
from eth_utils import keccak
from fastapi import APIRouter, Depends, HTTPException, Path

from app.config import get_settings
from app.routers.auth import require_roles
from app.store import store
from app.tigergraph import graph_client

router = APIRouter(prefix="/chain", tags=["chain"])


def _topic(signature: str) -> str:
    return "0x" + keccak(text=signature).hex()


EVENTS = {
    _topic("Registered(bytes32,address,uint256)"): "registered",
    _topic("Vouched(bytes32,bytes32,uint32)"): "vouched",
    _topic("Activated(bytes32,address,uint64)"): "activated",
    _topic("Challenged(bytes32,address,uint256,uint64)"): "challenged",
    _topic("ChallengeResolved(bytes32,bool,address)"): "challenge_resolved",
    _topic("Revoked(bytes32,string)"): "revoked",
}


def _did(topic: str) -> str:
    return "did:trustgraph:" + topic.lower()


def _address(topic: str) -> str:
    return "0x" + topic[-40:].lower()


def _identity_did(wallet: str) -> str:
    return "did:trustgraph:0x" + keccak(text=wallet.lower()).hex()


def _get_person(did: str) -> dict:
    person = store.persons.get(did)
    if person is None:
        person = {
            "did": did,
            "wallet": "",
            "status": "pending",
            "country_hash": "",
            "biometric_hash": "",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "vouches": [],
        }
    return person


def _save_person(person: dict) -> None:
    person.setdefault("source", "base-sepolia")
    store.persons[person["did"]] = person
    graph_client.upsert_person(person)


@router.post("/index/{tx_hash}")
def index_registry_transaction(
    tx_hash: str = Path(pattern=r"^0x[0-9a-fA-F]{64}$"),
    session: dict = Depends(require_roles("receiver")),
) -> dict:
    settings = get_settings()
    if not settings.registry_configured:
        raise HTTPException(status_code=503, detail="Personhood registry is not configured")

    try:
        with httpx.Client(timeout=12.0) as client:
            chain_response = client.post(
                settings.base_sepolia_rpc_url,
                json={"jsonrpc": "2.0", "id": "trustgraph", "method": "eth_chainId", "params": []},
            )
            chain_response.raise_for_status()
            chain_id = chain_response.json().get("result")
            if chain_id != "0x14a34":
                raise HTTPException(status_code=503, detail="Configured RPC is not Base Sepolia (chain ID 84532)")
            response = client.post(
                settings.base_sepolia_rpc_url,
                json={"jsonrpc": "2.0", "id": "trustgraph", "method": "eth_getTransactionReceipt", "params": [tx_hash]},
            )
            response.raise_for_status()
            rpc = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Could not read transaction from Base Sepolia RPC") from exc

    if rpc.get("error"):
        raise HTTPException(status_code=502, detail="Base Sepolia RPC rejected the receipt request")
    receipt = rpc.get("result")
    if receipt is None:
        raise HTTPException(status_code=409, detail="Transaction is not mined yet")
    if receipt.get("status") != "0x1":
        raise HTTPException(status_code=400, detail="Transaction failed on Base Sepolia")

    registry = (settings.personhood_registry_address or "").lower()
    if (receipt.get("to") or "").lower() != registry:
        raise HTTPException(status_code=400, detail="Transaction did not call the configured personhood registry")

    applied = 0
    caller_wallet = session["wallet"].lower()
    for log in receipt.get("logs", []):
        if (log.get("address") or "").lower() != registry:
            continue
        topics = [value.lower() for value in log.get("topics", [])]
        event = EVENTS.get(topics[0]) if topics else None
        if event is None:
            continue

        if event in {"registered", "activated"}:
            did = _did(topics[1])
            wallet = _address(topics[2])
            if event == "registered" and wallet != caller_wallet:
                raise HTTPException(status_code=403, detail="Transaction event does not belong to the signed-in receiver")
            if did != _identity_did(wallet):
                raise HTTPException(status_code=400, detail="Registry DID hash does not match the wallet identity")
            person = _get_person(did)
            if event == "activated" and person.get("wallet", "").lower() != wallet:
                raise HTTPException(status_code=409, detail="Index this person's registration transaction before their activation")
            person["wallet"] = wallet
            person["status"] = "pending" if event == "registered" else "active"
            timestamp = datetime.now(timezone.utc).isoformat()
            person["registered_at"] = person.get("registered_at") or timestamp
            if event == "activated":
                person["active_at"] = timestamp
            _save_person(person)
            applied += 1
        elif event == "vouched":
            target_did, voucher_did = _did(topics[1]), _did(topics[2])
            voucher = store.persons.get(voucher_did)
            if not voucher or voucher.get("wallet", "").lower() != caller_wallet or voucher.get("status") != "active":
                raise HTTPException(status_code=403, detail="Vouch event does not belong to an active signed-in receiver")
            target = _get_person(target_did)
            if voucher_did not in target["vouches"]:
                target["vouches"].append(voucher_did)
                _save_person(target)
                graph_client.upsert_vouch(voucher_did, target_did)
            applied += 1
        elif event == "challenged":
            did = _did(topics[1])
            challenger_wallet = _address(topics[2])
            challenger_did = _identity_did(challenger_wallet)
            challenger = _get_person(challenger_did)
            challenger["wallet"] = challenger_wallet
            _save_person(challenger)
            person = _get_person(did)
            person["status"] = "challenged"
            person["challenger_did"] = challenger_did
            _save_person(person)
            graph_client.upsert_challenge(challenger_did, did, "pending", datetime.now(timezone.utc).isoformat())
            applied += 1
        elif event == "revoked":
            did = _did(topics[1])
            person = _get_person(did)
            person["status"] = "revoked"
            _save_person(person)
            applied += 1
        elif event == "challenge_resolved":
            did = _did(topics[1])
            upheld = int(log.get("data", "0x0")[2:66], 16) == 1
            person = _get_person(did)
            person["status"] = "revoked" if upheld else "active"
            if not upheld:
                person["active_at"] = datetime.now(timezone.utc).isoformat()
            _save_person(person)
            challenger_did = person.get("challenger_did")
            if challenger_did:
                graph_client.upsert_challenge(
                    challenger_did, did, "upheld" if upheld else "dismissed", datetime.now(timezone.utc).isoformat()
                )
            applied += 1

    if applied == 0:
        raise HTTPException(status_code=400, detail="No supported personhood registry events found")
    return {"transaction_hash": tx_hash, "indexed_events": applied, "source": "base-sepolia"}
