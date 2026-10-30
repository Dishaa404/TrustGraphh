def create_intent(client, asset="XMR", provider="cake"):
    response = client.post(
        "/payments/intent",
        json={
            "payer_did": "did:trustgraph:alice",
            "amount": 5.5,
            "asset": asset,
            "provider": provider,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_cake_intent_for_monero(client):
    intent = create_intent(client)

    assert intent["provider"] == "cake"
    assert intent["asset"] == "XMR"
    assert intent["status"] == "pending"
    assert intent["address"].startswith("8")
    assert intent["uri"].startswith("trustgraph://pay/")


def test_rodo_sandbox_intent_for_usdc(client):
    intent = create_intent(client, asset="USDC", provider="rodo")

    assert intent["provider"] == "rodo"
    assert intent["address"].startswith("0x")


def test_webhook_confirms_payment(client):
    intent = create_intent(client)

    response = client.post(
        "/payments/webhook",
        json={
            "payment_id": intent["id"],
            "status": "confirmed",
            "tx_hash": "0xdeadbeef",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["tx_hash"] == "0xdeadbeef"

    fetched = client.get(f"/payments/{intent['id']}")
    assert fetched.json()["status"] == "confirmed"


def test_unknown_payment_returns_404(client):
    assert client.get("/payments/pay_missing").status_code == 404
