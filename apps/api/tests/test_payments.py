from eth_utils import keccak
from conftest import login


def create_intent(client, asset="XMR", provider="cake"):
    account, headers = login(client, "donor")
    payer_did = "did:trustgraph:0x" + keccak(text=account.address.lower()).hex()
    response = client.post(
        "/payments/intent",
        json={
            "payer_did": payer_did,
            "payer_wallet": account.address,
            "amount": 5.5,
            "asset": asset,
            "provider": provider,
        }, headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_cake_without_wallet_rpc_does_not_create_fake_invoice(client):
    account, headers = login(client, "donor")
    response = client.post(
        "/payments/intent",
        json={"payer_did": "did:trustgraph:0x" + keccak(text=account.address.lower()).hex(), "payer_wallet": account.address, "amount": 1, "asset": "XMR", "provider": "cake"}, headers=headers,
    )
    assert response.status_code == 503


def test_unconfigured_rodo_does_not_create_fake_invoice(client):
    account, headers = login(client, "donor")
    response = client.post(
        "/payments/intent",
        json={"payer_did": "did:trustgraph:0x" + keccak(text=account.address.lower()).hex(), "payer_wallet": account.address, "amount": 1, "asset": "USDC", "provider": "rodo"}, headers=headers,
    )
    assert response.status_code == 503


def test_webhook_confirms_payment(client, monkeypatch):
    from app.config import Settings
    from app.routers import payments
    from app.store import store

    intent = {"id": "pay_test", "provider": "rodo", "status": "pending", "provider_data": {}}
    with store.lock:
        store.payments[intent["id"]] = intent

    monkeypatch.setattr(payments, "get_settings", lambda: Settings(rodo_webhook_secret="test-secret"))

    response = client.post(
        "/payments/webhook",
        json={
            "payment_id": intent["id"],
            "status": "confirmed",
            "tx_hash": "0xdeadbeef",
        },
        headers={"X-Webhook-Secret": "test-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["tx_hash"] == "0xdeadbeef"

    from app.config import Settings
    from app.routers import auth
    from eth_account import Account
    account = Account.create()
    monkeypatch.setattr(auth, "get_settings", lambda: Settings(verified_ngo_wallets=account.address))
    _, headers = login(client, "ngo", account=account)
    fetched = client.get(f"/payments/{intent['id']}", headers=headers)
    assert fetched.json()["status"] == "confirmed"


def test_unknown_payment_returns_404(client):
    _, headers = login(client, "donor")
    assert client.get("/payments/pay_missing", headers=headers).status_code == 404
