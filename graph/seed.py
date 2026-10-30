"""Seed the TrustGraph demo dataset.

Creates 60 people, 3 issuers, credentials, vouches, devices, challenges, payments,
and two planted sybil rings so the detection query has something to find.

Usage:
    python seed.py
"""

from __future__ import annotations

import hashlib
import os
import random
import sys

import pyTigerGraph as tg
from dotenv import load_dotenv

ROOT = os.path.dirname(__file__)
load_dotenv(os.path.join(ROOT, ".env"))

GRAPH = os.environ.get("TG_GRAPH", "TrustGraph")
RNG = random.Random(42)

NOW = "2026-10-01 12:00:00"
PERSON_IDS = [f"did:trustgraph:person-{i:03d}" for i in range(60)]
TRUSTED = PERSON_IDS[:5]
PENDING = PERSON_IDS[40:45]
RING_A = PERSON_IDS[50:55]
RING_B = PERSON_IDS[55:60]
SYBILS = set(RING_A) | set(RING_B)

ISSUERS = {
    "issuer:gov": ("Government Registry", 3),
    "issuer:uni": ("State University", 2),
    "issuer:employer": ("Verified Employer Network", 2),
}

CREDENTIAL_TYPES = ["kyc", "education", "employment"]
COUNTRIES = ["US", "IN", "GB", "DE", "BR", "NG"]


def short_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def wallet_for(did: str) -> str:
    return "0x" + short_hash(did)[:40]


def connect() -> tg.TigerGraphConnection:
    host = os.environ.get("TG_HOST")
    username = os.environ.get("TG_USERNAME")
    password = os.environ.get("TG_PASSWORD")
    secret = os.environ.get("TG_SECRET", "")

    if not host or not username or not password:
        sys.exit("Set TG_HOST, TG_USERNAME and TG_PASSWORD first.")

    conn = tg.TigerGraphConnection(
        host=host,
        username=username,
        password=password,
        graphname=GRAPH,
        tgCloud=True,
    )
    if secret:
        conn.getToken(secret)
    return conn


def add_person(conn: tg.TigerGraphConnection, did: str) -> None:
    if did in SYBILS:
        trust = RNG.randint(4, 12)
    elif did in TRUSTED:
        trust = RNG.randint(94, 99)
    elif did in PENDING:
        trust = 0
    else:
        trust = RNG.randint(25, 78)

    status = "pending" if did in PENDING else "active"
    wallet = wallet_for(did)

    conn.upsertVertex(
        "Person",
        did,
        {
            "wallet": wallet,
            "status": status,
            "country_hash": short_hash(RNG.choice(COUNTRIES)),
            "biometric_hash": short_hash(f"bio:{did}"),
            "registered_at": NOW,
            "active_at": NOW if status == "active" else "1970-01-01 00:00:00",
            "trust_score": float(trust),
            "source": "seed",
        },
    )
    conn.upsertVertex("Wallet", wallet, {"chain": "base-sepolia"})
    conn.upsertEdge("Person", did, "HAS_WALLET", "Wallet", wallet)


def add_vouch(conn: tg.TigerGraphConnection, src: str, tgt: str, weight: float = 1.0) -> None:
    if src == tgt:
        return
    conn.upsertEdge(
        "Person",
        src,
        "VOUCHED",
        "Person",
        tgt,
        {"weight": weight, "created_at": NOW},
    )


def add_credential(conn: tg.TigerGraphConnection, did: str, index: int, issuer: str) -> None:
    credential_id = f"cred:{did}:{index}"
    credential_type = RNG.choice(CREDENTIAL_TYPES)
    status = "revoked" if RNG.random() < 0.06 else "valid"

    conn.upsertVertex(
        "Credential",
        credential_id,
        {
            "credential_type": credential_type,
            "content_hash": short_hash(f"content:{credential_id}"),
            "cid": f"ipfs://bafy-{short_hash(credential_id)[:24]}",
            "status": status,
            "issued_at": NOW,
            "expires_at": "2028-10-01 12:00:00",
        },
    )
    conn.upsertEdge("Person", did, "HOLDS", "Credential", credential_id)
    conn.upsertEdge("Credential", credential_id, "ATTESTED_BY", "Issuer", issuer)


def add_device(conn: tg.TigerGraphConnection, did: str, fingerprint: str, platform: str) -> None:
    conn.upsertVertex("Device", fingerprint, {"platform": platform})
    conn.upsertEdge("Person", did, "USED_DEVICE", "Device", fingerprint)


def add_challenge(conn: tg.TigerGraphConnection, challenger: str, target: str, index: int) -> None:
    challenge_id = f"challenge:{index}"
    outcome = "upheld" if index % 2 == 0 else "rejected"

    conn.upsertVertex(
        "Challenge",
        challenge_id,
        {
            "reason": "sybil suspicion",
            "status": "resolved",
            "stake": 0.002,
            "created_at": NOW,
        },
    )
    conn.upsertEdge(
        "Person",
        challenger,
        "CHALLENGED",
        "Person",
        target,
        {"reason": "sybil suspicion", "outcome": outcome, "created_at": NOW},
    )


def add_payment(conn: tg.TigerGraphConnection, did: str, index: int) -> None:
    payment_id = f"payment:{index}"
    conn.upsertVertex(
        "Payment",
        payment_id,
        {
            "provider": RNG.choice(["cake", "rodo"]),
            "asset": RNG.choice(["XMR", "USDC", "BTC"]),
            "amount": round(RNG.uniform(1, 25), 2),
            "tx_hash": "0x" + short_hash(payment_id),
            "status": "confirmed",
        },
    )
    conn.upsertEdge("Person", did, "PAID_BY", "Payment", payment_id)


def main() -> None:
    conn = connect()

    for issuer_id, (name, tier) in ISSUERS.items():
        conn.upsertVertex("Issuer", issuer_id, {"name": name, "trust_tier": tier})

    for community_id, label in [
        ("community:humans", "verified humans"),
        ("community:ring-a", "planted ring A"),
        ("community:ring-b", "planted ring B"),
    ]:
        conn.upsertVertex(
            "Community",
            community_id,
            {"algorithm": "seed", "label": label},
        )

    for did in PERSON_IDS:
        add_person(conn, did)
        assignment = "community:humans"
        if did in RING_A:
            assignment = "community:ring-a"
        elif did in RING_B:
            assignment = "community:ring-b"
        conn.upsertEdge("Person", did, "MEMBER_OF", "Community", assignment)

    # Credentials
    for did in PERSON_IDS:
        if did in PENDING:
            continue
        count = 0 if did in SYBILS else RNG.randint(1, 4)
        for index in range(count):
            add_credential(conn, did, index, RNG.choice(list(ISSUERS)))

    # Organic vouches from the trusted seed set
    for trusted in TRUSTED:
        candidates = [p for p in PERSON_IDS if p != trusted and p not in SYBILS]
        for target in RNG.sample(candidates, 8):
            add_vouch(conn, trusted, target, weight=1.5)

    # Long-tail vouches between regular humans
    regular = [p for p in PERSON_IDS if p not in TRUSTED and p not in PENDING and p not in SYBILS]
    for did in regular:
        candidates = [p for p in regular if p != did]
        for target in RNG.sample(candidates, RNG.randint(1, 3)):
            add_vouch(conn, did, target, weight=1.0)

    # Planted sybil rings: full mutual vouching inside each ring
    for ring in (RING_A, RING_B):
        for src in ring:
            for tgt in ring:
                if src != tgt:
                    add_vouch(conn, src, tgt, weight=1.0)

    # Only weak bridges from rings to the honest graph
    for ring, bridge in [(RING_A, TRUSTED[0]), (RING_B, TRUSTED[1])]:
        add_vouch(conn, bridge, ring[0], weight=0.5)
        add_vouch(conn, ring[0], bridge, weight=0.5)

    # Devices: household sharing among honest users, shared devices inside rings
    for index, did in enumerate(regular):
        if index % 7 == 0 and index + 1 < len(regular):
            add_device(conn, did, f"dev-house-{index // 7}", "mobile")
            add_device(conn, regular[index + 1], f"dev-house-{index // 7}", "mobile")
        else:
            add_device(conn, did, f"dev-{did[-3:]}", RNG.choice(["mobile", "desktop"]))

    for did in RING_A:
        add_device(conn, did, "dev-ring-a-1", "android-emulator")
        add_device(conn, did, "dev-ring-a-2", "android-emulator")
    for did in RING_B:
        add_device(conn, did, "dev-ring-b-1", "android-emulator")

    # Challenges against a few regular accounts
    for index, target in enumerate(RNG.sample(regular, 5)):
        add_challenge(conn, TRUSTED[index % len(TRUSTED)], target, index)

    # Payments
    for index, did in enumerate(RNG.sample([p for p in PERSON_IDS if p not in PENDING], 12)):
        add_payment(conn, did, index)

    print(f"Seeded {len(PERSON_IDS)} people, {len(TRUSTED)} trusted seeds, "
          f"{len(RING_A) + len(RING_B)} planted sybils.")

    try:
        result = conn.runInstalledQuery(
            "sybil_rings", {"min_mutual": 2, "min_devices": 2}
        )
        print("sybil_rings ->", result)
    except Exception as exc:  # noqa: BLE001
        print("Queries are not installed yet; run install.py first.", exc)


if __name__ == "__main__":
    main()
