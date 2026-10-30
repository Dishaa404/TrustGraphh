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


def test_role_is_bound_to_login_challenge_and_me_endpoint(client):
    from conftest import login

    account, headers = login(client, "receiver")
    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "receiver"
    assert me.json()["wallet"] == account.address.lower()
    assert client.post("/auth/logout", headers=headers).status_code == 200
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_ngo_login_is_pending_and_can_apply(client):
    from conftest import login

    _, headers = login(client, "ngo")
    assert client.get("/auth/me", headers=headers).json()["approval_status"] == "pending"
    response = client.post("/auth/ngo/application", headers=headers, json={
        "organization_name": "Example NGO", "registration_id": "REG-123", "website": "https://example.org"
    })
    assert response.status_code == 201
    assert response.json()["status"] == "pending"
