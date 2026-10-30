from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.config import Settings
from app.payments.base import PaymentIntent, PaymentProvider, PaymentProviderError

ATOMIC_UNITS = Decimal("1000000000000")


class CakeWalletProvider(PaymentProvider):
    """Create XMR invoices on a merchant Monero wallet used with Cake Wallet.

    Cake Wallet is the payer app. A merchant-owned, authenticated monero-wallet-rpc
    service provides a unique receive subaddress per invoice; the payer scans the
    Monero URI with Cake Wallet. This adapter never invents payment addresses.
    """

    name = "cake"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.cake_wallet_configured:
            raise PaymentProviderError("Cake Wallet payments are unavailable: configure authenticated Monero wallet RPC.")

        url = self.settings.cake_monero_wallet_rpc_url or ""
        if not url.rstrip("/").endswith("/json_rpc"):
            url = url.rstrip("/") + "/json_rpc"
        try:
            response = httpx.post(
                url,
                json={"jsonrpc": "2.0", "id": "trustgraph", "method": method, "params": params},
                auth=(
                    self.settings.cake_monero_wallet_rpc_user or "",
                    self.settings.cake_monero_wallet_rpc_password or "",
                ),
                timeout=15.0,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise PaymentProviderError("Could not reach the configured Monero wallet RPC.") from exc
        if payload.get("error"):
            raise PaymentProviderError("Monero wallet RPC rejected the request.")
        result = payload.get("result")
        if not isinstance(result, dict):
            raise PaymentProviderError("Monero wallet RPC returned an invalid response.")
        return result

    @staticmethod
    def _atomic_amount(amount: float) -> int:
        try:
            exact = Decimal(str(amount))
            atomic = exact * ATOMIC_UNITS
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("XMR amount must be a valid decimal") from exc
        if exact <= 0 or atomic != atomic.to_integral_value():
            raise ValueError("XMR amount must be positive and have at most 12 decimal places")
        return int(atomic)

    def create_intent(self, payer_did: str, amount: float, asset: str) -> PaymentIntent:
        if asset.upper() != "XMR":
            raise ValueError("Cake Wallet adapter currently supports XMR only")
        atomic_amount = self._atomic_amount(amount)
        now = datetime.now(timezone.utc)
        payment_id = "pay_" + secrets.token_hex(12)

        try:
            created = self._rpc(
                "create_address",
                {"account_index": 0, "label": f"TrustGraph {payment_id}"},
            )
            address = created.get("address")
            address_index = created.get("address_index")
            if not isinstance(address, str) or not address or not isinstance(address_index, int):
                raise PaymentProviderError("Monero wallet RPC did not return a receive subaddress.")

            payment_uri = self._rpc(
                "make_uri",
                {
                    "address": address,
                    "amount": atomic_amount,
                    "recipient_name": "TrustGraph",
                    "tx_description": f"Payment {payment_id}",
                },
            ).get("uri")
            if not isinstance(payment_uri, str) or not payment_uri.startswith("monero:"):
                raise PaymentProviderError("Monero wallet RPC did not return a valid payment URI.")
        except PaymentProviderError:
            raise

        return PaymentIntent(
            id=payment_id,
            provider=self.name,
            payer_did=payer_did,
            asset="XMR",
            amount=amount,
            address=address,
            status="pending",
            created_at=now.isoformat(),
            expires_at=(now + timedelta(minutes=30)).isoformat(),
            uri=payment_uri,
            provider_data={"subaddress_index": address_index, "expected_atomic": atomic_amount},
        )

    def get_status(self, payment_id: str, current: str, provider_data: dict | None = None) -> str:
        if current == "confirmed":
            return current
        index = (provider_data or {}).get("subaddress_index")
        expected = (provider_data or {}).get("expected_atomic")
        if not isinstance(index, int) or not isinstance(expected, int):
            raise PaymentProviderError("Payment intent is missing its Monero invoice details.")
        transfers = self._rpc(
            "get_transfers",
            {"in": True, "pool": True, "account_index": 0, "subaddr_indices": [index]},
        )
        incoming = transfers.get("in", []) + transfers.get("pool", [])
        if not incoming:
            return current
        valid = [tx for tx in incoming if not tx.get("double_spend_seen", False)]
        received = sum(int(tx.get("amount", 0)) for tx in valid)
        confirmed_received = sum(
            int(tx.get("amount", 0)) for tx in valid if int(tx.get("confirmations", 0)) >= 1
        )
        if received < expected:
            (provider_data or {}).update({"received_atomic": received})
            return "underpaid"
        if confirmed_received < expected:
            (provider_data or {}).update({"received_atomic": received})
            return "confirming"
        (provider_data or {}).update(
            {"received_atomic": received, "tx_hash": valid[-1].get("txid")}
        )
        return "confirmed"
