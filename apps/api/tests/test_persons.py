from conftest import login


def create_person(client, wallet: str, **overrides):
    from eth_account import Account
    account = Account.create()
    payload = {"wallet": account.address, **overrides}
    _, headers = login(client, "receiver", account=account)
    response = client.post("/persons", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    person = response.json()
    person["_account"] = account
    return person


def test_create_and_fetch_person(client):
    person = create_person(client, "0xabc123", country="US")

    assert person["did"].startswith("did:trustgraph:")
    assert person["status"] == "pending"
    assert person["country_hash"]

    fetched = client.get(f"/persons/{person['did']}")
    assert fetched.status_code == 200
    assert fetched.json()["wallet"] == person["wallet"]


def test_duplicate_did_is_rejected(client):
    person = create_person(client, "0xabc123")

    from eth_account import Account
    account = Account.create()
    _, headers = login(client, "receiver", account=account)
    response = client.post(
        "/persons",
        json={"wallet": account.address, "did": person["did"]}, headers=headers,
    )

    assert response.status_code == 409


def test_api_does_not_forge_vouches_off_chain(client):
    target = create_person(client, "0xtarget")
    voucher = create_person(client, "0xvoucher")
    _, headers = login(client, "receiver", account=voucher["_account"])
    response = client.post(
        f"/persons/{target['did']}/vouch",
        json={"voucher_did": voucher["did"]}, headers=headers,
    )
    assert response.status_code == 409
    assert "Base Sepolia registry" in response.json()["detail"]


def test_trust_score_reports_unconfigured_graph(client):
    person = create_person(client, "0xtrust")

    response = client.get(f"/persons/{person['did']}/trust")

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "unconfigured"


def test_graph_endpoints_report_unconfigured(client):
    rings = client.get("/graph/rings")
    explain = client.get("/graph/explain/did:trustgraph:unindexed-person")

    assert rings.status_code == 200
    assert rings.json()["flagged"] == []
    assert rings.json()["source"] == "unconfigured"
    assert explain.status_code == 200
    assert explain.json()["source"] == "unconfigured"
