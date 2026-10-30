from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from app.config import Settings
from app.payments.base import PaymentIntent, PaymentProvider, PaymentProviderError


class RodoPaymentProvider(PaymentProvider):
    """Rodo Payments adapter.

    This optional adapter requires real Rodo credentials; it never fabricates an
    address or returns a payment intent that cannot receive funds.
    """

    name = "rodo"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _remote_create(self, payer_did: str, amount: float, asset: str) -> dict:
        if not (self.settings.rodo_api_base_url and self.settings.rodo_api_key):
            raise PaymentProviderError("Rodo is unavailable: configure RODO_API_BASE_URL and RODO_API_KEY.")

        try:
            response = httpx.post(
                f"{self.settings.rodo_api_base_url.rstrip('/')}/payments",
                headers={"Authorization": f"Bearer {self.settings.rodo_api_key}"},
                json={"payer_did": payer_did, "amount": amount, "asset": asset.upper()},
                timeout=15.0,
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise PaymentProviderError("Could not reach the configured Rodo payment API.") from exc

    def create_intent(self, payer_did: str, amount: float, asset: str) -> PaymentIntent:
        remote = self._remote_create(payer_did, amount, asset)
        payment_id = remote.get("id")
        address = remote.get("address")
        if not isinstance(payment_id, str) or not isinstance(address, str) or not address:
            raise PaymentProviderError("Rodo did not return an intent ID and deposit address.")
        now = datetime.now(timezone.utc)

        return PaymentIntent(
            id=payment_id,
            provider=self.name,
            payer_did=payer_did,
            asset=asset.upper(),
            amount=amount,
            address=address,
            status=remote.get("status", "pending"),
            created_at=now.isoformat(),
            expires_at=(now + timedelta(minutes=30)).isoformat(),
            uri=remote.get("uri", ""),
        )
