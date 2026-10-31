from __future__ import annotations

import hashlib
from datetime import datetime
from threading import Lock
from typing import Any

from app.config import Settings, get_settings


class GraphClient:
    """Thin wrapper around pyTigerGraph with a deterministic demo fallback.

    The fallback keeps the API and frontend usable before a Savanna instance is
    connected. It is clearly labelled with source="demo".
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._connection: Any | None = None
        self._lock = Lock()

    @property
    def configured(self) -> bool:
        return self.settings.tigergraph_configured

    def _conn(self) -> Any:
        if not self.configured:
            raise RuntimeError("TigerGraph is not configured")

        with self._lock:
            if self._connection is None:
                import pyTigerGraph as tg

                connection = tg.TigerGraphConnection(
                    host=self.settings.tg_host,
                    graphname=self.settings.tg_graph,
                    gsqlSecret=self.settings.tg_secret,
                )
                connection.getToken(self.settings.tg_secret)
                self._connection = connection

        return self._connection

    def _run(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        rows = self._conn().runInstalledQuery(query, params)
        return self._normalize(rows)

    @staticmethod
    def _normalize(rows: Any) -> list[dict[str, Any]]:
        if not isinstance(rows, list):
            return []
        normalized: list[dict[str, Any]] = []
        for row in rows:
            if isinstance(row, dict):
                normalized.append({key.lstrip("@"): value for key, value in row.items()})
        return normalized

    def trust_score(self, did: str) -> dict[str, Any]:
        if not self.configured:
            seed = int(hashlib.sha256(did.encode()).hexdigest()[:8], 16)
            return {
                "did": did,
                "trust_score": float(40 + seed % 45),
                "vouch_score": 0.0,
                "vouch_count": 0,
                "credential_score": 0.0,
                "challenge_penalty": 0,
                "device_penalty": 0,
                "source": "demo",
            }

        rows = self._run("trust_score", {"did": did})
        if not rows:
            return {"did": did, "trust_score": 0.0, "source": "tigergraph"}
        return {"did": did, **rows[0], "source": "tigergraph"}

    def explain_trust(self, did: str) -> dict[str, Any]:
        if not self.configured:
            return {
                "did": did,
                "vouchers": [],
                "credentials": [],
                "devices": [],
                "upheld_challenges": [],
                "source": "demo",
            }

        rows = self._run("explain_trust", {"did": did})
        payload = rows[0] if rows else {}
        return {"did": did, **payload, "source": "tigergraph"}

    def sybil_rings(self, min_mutual: int = 2, min_devices: int = 2) -> dict[str, Any]:
        if not self.configured:
            return {"flagged": [], "source": "demo"}

        rows = self._run(
            "sybil_rings",
            {"min_mutual": min_mutual, "min_devices": min_devices},
        )
        flagged = rows[0].get("flagged", []) if rows else []
        return {"flagged": flagged, "source": "tigergraph"}

    def upsert_person(self, person: dict[str, Any]) -> None:
        if not self.configured:
            return
        connection = self._conn()
        did = person["did"]
        wallet = person.get("wallet") or ""
        connection.upsertVertex(
            "Person",
            did,
            {
                "wallet": wallet,
                "status": person.get("status", "pending"),
                "country_hash": person.get("country_hash", ""),
                "biometric_hash": person.get("biometric_hash", ""),
                "registered_at": _graph_datetime(person.get("registered_at") or person.get("created_at")),
                "active_at": _graph_datetime(person.get("active_at")),
                "trust_score": float(person.get("trust_score", 0.0)),
                "source": person.get("source", "api"),
            },
        )
        if wallet:
            connection.upsertVertex("Wallet", wallet, {"chain": "base-sepolia"})
            connection.upsertEdge("Person", did, "HAS_WALLET", "Wallet", wallet)

    def upsert_credential(self, credential: dict[str, Any]) -> None:
        if not self.configured:
            return
        connection = self._conn()
        issuer = credential["issuer"].lower()
        connection.upsertVertex(
            "Credential",
            credential["id"],
            {
                "credential_type": credential["credential_type"],
                "content_hash": credential["content_hash"],
                "cid": credential["cid"],
                "status": credential["status"],
                "issued_at": _graph_datetime(credential["issued_at"]),
                "expires_at": _graph_datetime(credential.get("expires_at")),
            },
        )
        connection.upsertVertex("Issuer", issuer, {"name": issuer, "trust_tier": 1})
        connection.upsertEdge("Person", credential["subject_did"], "HOLDS", "Credential", credential["id"])
        connection.upsertEdge("Credential", credential["id"], "ATTESTED_BY", "Issuer", issuer)

    def upsert_challenge(self, source_did: str, target_did: str, outcome: str, created_at: str | None = None) -> None:
        if not self.configured:
            return
        self._conn().upsertEdge(
            "Person", source_did, "CHALLENGED", "Person", target_did,
            {"reason": "registry challenge", "outcome": outcome, "created_at": _graph_datetime(created_at)},
        )

    def upsert_vouch(self, source_did: str, target_did: str, weight: float = 1.0) -> None:
        if not self.configured:
            return
        self._conn().upsertEdge(
            "Person",
            source_did,
            "VOUCHED",
            "Person",
            target_did,
            {
                "weight": weight,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        )

    def upsert_payment(self, payment: dict[str, Any]) -> None:
        if not self.configured:
            return
        payer_did = payment["payer_did"]
        wallet = payment.get("payer_wallet") or ""
        connection = self._conn()
        if connection.getVertexData("Person", payer_did):
            connection.upsertVertex("Person", payer_did, {"wallet": wallet})
        else:
            connection.upsertVertex(
                "Person",
                payer_did,
                {
                    "wallet": wallet,
                    "status": "pending",
                    "country_hash": "",
                    "biometric_hash": "",
                    "trust_score": 0.0,
                    "source": "payment",
                },
            )
        if wallet:
            connection.upsertVertex("Wallet", wallet, {"chain": "base-sepolia"})
            connection.upsertEdge("Person", payer_did, "HAS_WALLET", "Wallet", wallet)
        connection.upsertVertex(
            "Payment",
            payment["id"],
            {
                "provider": payment["provider"],
                "asset": payment["asset"],
                "amount": float(payment["amount"]),
                "tx_hash": payment.get("provider_data", {}).get("tx_hash", ""),
                "status": payment["status"],
            },
        )
        connection.upsertEdge("Person", payer_did, "PAID_BY", "Payment", payment["id"])

    def service_status(self) -> str:
        if not self.configured:
            return "demo"
        try:
            self._conn().getInstalledQueries()
        except Exception:  # noqa: BLE001
            return "unavailable"
        return "connected"


graph_client = GraphClient()


def _graph_datetime(value: str | None) -> str:
    if not value:
        return "1970-01-01 00:00:00"
    return value.replace("T", " ").replace("Z", "")[:19]
