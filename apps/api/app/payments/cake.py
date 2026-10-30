from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import httpx

from app.config import Settings
from app.payments.base import PaymentIntent, PaymentProvider


class CakeWalletProvider(PaymentProvider):
    """Cake Wallet adapter.

    XMR/BTC addresses are generated locally for the demo. When the Monero wallet RPC
    is configured, `_integrated_address` asks the wallet for a subaddress instead,
    so each payment intent can be reconciled independently.
    """

    name = "cake"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _rpc(self, method: str, params: dict | None = None) -> dict | None:
        url = self.settings.cake_monero_wallet_rpc_url
        if not url:
            return None

        auth = None
        if self.settings.cake_monero_wallet_rpc_user:
            auth = (
                self.settings.cake_monero_wallet_rpc_user,
                self.settings.cake_monero_wallet_rpc_password or "",
            )

        response = httpx.post(
            url,
            json={"jsonrpc": "2.0", "id": "trustgraph", "method": method, "params": params or {}},
            auth=auth,
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json().get("result")

    def _integrated_address(self) -> str | None:
        try:
            result = self._rpc("make_integrated_address", {})
        except httpx.HTTPError:
            return None
        if not result:
            return None
        return result.get("integrated_address")

    @staticmethod
    def _local_address(asset: str) -> str:
        digest = hashlib.sha256(f"{asset}:{secrets.token_hex(16)}".encode()).hexdigest()
        upper = asset.upper()
        if upper == "XMR":
            return "8" + digest[:94]
        if upper == "BTC":
            return "bc1q" + digest[:38]
        return "0x" + digest[:40]

    def create_intent(self, payer_did: str, amount: float, asset: str) -> PaymentIntent:
        now = datetime.now(timezone.utc)
        payment_id = "pay_" + secrets.token_hex(8)

        address = None
        if asset.upper() == "XMR":
            address = self._integrated_address()
        address = address or self._local_address(asset)

        return PaymentIntent(
            id=payment_id,
            provider=self.name,
            payer_did=payer_did,
            asset=asset.upper(),
            amount=amount,
            address=address,
            status="pending",
            created_at=now.isoformat(),
            expires_at=(now + timedelta(minutes=30)).isoformat(),
            uri=f"trustgraph://pay/{payment_id}",
        )
