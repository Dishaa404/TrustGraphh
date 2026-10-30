from app.config import Settings
from app.payments.cake import CakeWalletProvider
from app.payments.base import PaymentProviderError


def make_provider():
    return CakeWalletProvider(
        Settings(
            cake_monero_wallet_rpc_url="http://127.0.0.1:18088/json_rpc",
            cake_monero_wallet_rpc_user="user",
            cake_monero_wallet_rpc_password="password",
        )
    )


def test_cake_adapter_creates_invoice_from_wallet_rpc(monkeypatch):
    provider = make_provider()
    calls = []

    def rpc(method, params):
        calls.append((method, params))
        if method == "create_address":
            return {"address": "stagenet-subaddress", "address_index": 7}
        return {"uri": "monero:stagenet-subaddress?tx_amount=0.25"}

    monkeypatch.setattr(provider, "_rpc", rpc)
    intent = provider.create_intent("did:trustgraph:alice", 0.25, "XMR")

    assert intent.address == "stagenet-subaddress"
    assert intent.uri.startswith("monero:")
    assert intent.provider_data == {"subaddress_index": 7, "expected_atomic": 250_000_000_000}
    assert calls[0][0] == "create_address"
    assert calls[1][0] == "make_uri"
    assert calls[1][1]["amount"] == 250_000_000_000


def test_cake_status_waits_for_full_amount_and_confirmation(monkeypatch):
    provider = make_provider()
    data = {"subaddress_index": 7, "expected_atomic": 250}
    transfers = {"in": [{"amount": 250, "confirmations": 0}], "pool": []}
    monkeypatch.setattr(provider, "_rpc", lambda method, params: transfers)

    assert provider.get_status("pay_test", "pending", data) == "confirming"
    transfers["in"][0]["confirmations"] = 1
    assert provider.get_status("pay_test", "confirming", data) == "confirmed"


def test_cake_requires_real_wallet_rpc():
    provider = CakeWalletProvider(Settings())
    try:
        provider.create_intent("did:trustgraph:alice", 1, "XMR")
    except PaymentProviderError as exc:
        assert "authenticated Monero wallet RPC" in str(exc)
    else:
        raise AssertionError("an unconfigured provider must not return a fake address")
