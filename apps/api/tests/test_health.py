def test_health_reports_demo_mode(client):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["services"]["tigergraph"] == "demo"
    assert body["services"]["payments"] == "unconfigured"
    assert body["services"]["payment_provider"] == "cake"


def test_root_points_at_docs(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["docs"] == "/docs"
