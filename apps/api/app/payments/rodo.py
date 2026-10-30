from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import httpx

from app.config import Settings
from app.payments.base import PaymentIntent, PaymentProvider


class RodoPaymentProvider(PaymentProvider):
    """Rodo Payments adapter.

    If RODO_API_BASE_URL and RODO_API_KEY are set, the intent is created through
    Rodo. Otherwise it falls back to a deterministic sandbox intent so the flow
    stays demoable while the Rodo API details are being confirmed.
    """

    name = "rodo"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _remote_create(self, payer_did: str, amount: float, asset: str) -> dict | None:
        if not (self.settings.rodo_api_base_url and self.settings.rodo_api_key):
            return None

        response = httpx.post(
            f"{self.settings.rodo_api_base_url.rstrip('/')}/payments",
            headers={"Authorization": f"Bearer {self.settings.rodo_api_key}"},
            json={"payer_did": payer_did, "amount": amount, "asset": asset.upper()},
            timeout=15.0,
        )
        response.raise_for_status()
        return response.json()

    def create_intent(self, payer_did: str, amount: float, asset: str) -> PaymentIntent:
        now = datetime.now(timezone.utc)
        payment_id = "pay_" + secrets.token_hex(8)

        remote = self._remote_create(payer_did, amount, asset)
        if remote:
            payment_id = remote.get("id", payment_id)
            address = remote.get("address", "")
            status = remote.get("status", "pending")
        else:
            digest = hashlib.sha256(f"{payment_id}:{asset}".encode()).hexdigest()
            address = "0x" + digest[:40]
            status = "pending"

        return PaymentIntent(
            id=payment_id,
            provider=self.name,
            payer_did=payer_did,
            asset=asset.upper(),
            amount=amount,
            address=address,
            status=status,
            created_at=now.isoformat(),
            expires_at=(now + timedelta(minutes=30)).isoformat(),
            uri=f"trustgraph://pay/{payment_id}",
        )
