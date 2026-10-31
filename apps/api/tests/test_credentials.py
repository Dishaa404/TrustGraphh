def issue_credential(client, monkeypatch):
    from eth_account import Account
    from app.config import Settings
    from app.routers import auth
    from app.store import store
    from conftest import login
    account = Account.create()
    monkeypatch.setattr(auth, "get_settings", lambda: Settings(verified_ngo_wallets=account.address))
    _, headers = login(client, "ngo", account=account)
    store.persons["did:trustgraph:alice"] = {
        "did": "did:trustgraph:alice", "wallet": "0xsubject", "status": "active", "vouches": []
    }
    response = client.post(
        "/credentials",
        json={
            "subject_did": "did:trustgraph:alice",
            "issuer": account.address,
            "credential_type": "kyc",
            "content_hash": "0xcontent",
            "cid": "ipfs://bafy-test",
            "expires_at": "2028-01-01T00:00:00Z",
        }, headers=headers,
    )
    assert response.status_code == 201, response.text
    credential = response.json()
    credential["_headers"] = headers
    return credential


def test_issue_and_fetch_credential(client, monkeypatch):
    credential = issue_credential(client, monkeypatch)

    assert credential["status"] == "valid"
    assert credential["id"].startswith("cred:")

    fetched = client.get(f"/credentials/{credential['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["cid"] == "ipfs://bafy-test"


def test_revoke_credential(client, monkeypatch):
    credential = issue_credential(client, monkeypatch)

    revoked = client.post(
        f"/credentials/{credential['id']}/revoke",
        json={"reason": "employment ended"},
        headers=credential["_headers"],
    )

    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"
    assert revoked.json()["revocation_reason"] == "employment ended"


def test_unknown_credential_returns_404(client):
    assert client.get("/credentials/cred:missing").status_code == 404
