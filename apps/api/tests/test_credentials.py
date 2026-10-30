def issue_credential(client):
    response = client.post(
        "/credentials",
        json={
            "subject_did": "did:trustgraph:alice",
            "issuer": "0xissuer",
            "credential_type": "kyc",
            "content_hash": "0xcontent",
            "cid": "ipfs://bafy-test",
            "expires_at": "2028-01-01T00:00:00Z",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_issue_and_fetch_credential(client):
    credential = issue_credential(client)

    assert credential["status"] == "valid"
    assert credential["id"].startswith("cred:")

    fetched = client.get(f"/credentials/{credential['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["cid"] == "ipfs://bafy-test"


def test_revoke_credential(client):
    credential = issue_credential(client)

    revoked = client.post(
        f"/credentials/{credential['id']}/revoke",
        json={"reason": "employment ended"},
    )

    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"
    assert revoked.json()["revocation_reason"] == "employment ended"


def test_unknown_credential_returns_404(client):
    assert client.get("/credentials/cred:missing").status_code == 404
