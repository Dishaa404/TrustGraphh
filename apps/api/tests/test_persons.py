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


def test_three_vouches_activate_a_person(client):
    target = create_person(client, "0xtarget")
    vouchers = [create_person(client, f"0xvoucher{i}") for i in range(3)]

    for voucher in vouchers:
        _, headers = login(client, "receiver", account=voucher["_account"])
        response = client.post(
            f"/persons/{target['did']}/vouch",
            json={"voucher_did": voucher["did"]}, headers=headers,
        )
        assert response.status_code == 201, response.text

    fetched = client.get(f"/persons/{target['did']}").json()
    assert fetched["status"] == "active"
    assert len(fetched["vouches"]) == 3


def test_trust_score_has_demo_fallback(client):
    person = create_person(client, "0xtrust")

    response = client.get(f"/persons/{person['did']}/trust")

    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["trust_score"] <= 100
    assert body["source"] == "demo"


def test_graph_endpoints_in_demo_mode(client):
    rings = client.get("/graph/rings")
    explain = client.get("/graph/explain/did:trustgraph:person-001")

    assert rings.status_code == 200
    assert rings.json()["flagged"] == []
    assert explain.status_code == 200
    assert explain.json()["source"] == "demo"
