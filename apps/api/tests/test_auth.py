from eth_account import Account
from eth_account.messages import encode_defunct


def test_siwe_nonce_and_signature_round_trip(client):
    account = Account.create()

    nonce_response = client.post("/auth/nonce", json={"wallet": account.address})
    assert nonce_response.status_code == 200

    challenge = nonce_response.json()
    signed = account.sign_message(encode_defunct(text=challenge["message"]))

    verify_response = client.post(
        "/auth/verify",
        json={
            "wallet": account.address,
            "signature": signed.signature.hex(),
            "nonce": challenge["nonce"],
        },
    )

    assert verify_response.status_code == 200
    body = verify_response.json()
    assert body["authenticated"] is True
    assert body["address"].lower() == account.address.lower()
    assert body["token"]


def test_nonce_cannot_be_replayed(client):
    account = Account.create()
    challenge = client.post("/auth/nonce", json={"wallet": account.address}).json()
    signed = account.sign_message(encode_defunct(text=challenge["message"]))
    payload = {
        "wallet": account.address,
        "signature": signed.signature.hex(),
        "nonce": challenge["nonce"],
    }

    assert client.post("/auth/verify", json=payload).status_code == 200
    assert client.post("/auth/verify", json=payload).status_code == 400


def test_signature_from_wrong_wallet_is_rejected(client):
    account = Account.create()
    attacker = Account.create()
    challenge = client.post("/auth/nonce", json={"wallet": account.address}).json()
    signed = attacker.sign_message(encode_defunct(text=challenge["message"]))

    response = client.post(
        "/auth/verify",
        json={
            "wallet": account.address,
            "signature": signed.signature.hex(),
            "nonce": challenge["nonce"],
        },
    )

    assert response.status_code == 401
