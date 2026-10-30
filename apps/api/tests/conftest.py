import os

import pytest
from fastapi.testclient import TestClient

for key in [
    "TG_HOST",
    "TG_USERNAME",
    "TG_PASSWORD",
    "TG_SECRET",
    "RODO_API_BASE_URL",
    "RODO_API_KEY",
    "RODO_WEBHOOK_SECRET",
    "CAKE_MONERO_WALLET_RPC_URL",
]:
    os.environ[key] = ""

from app.main import app  # noqa: E402
from app.store import store  # noqa: E402


@pytest.fixture(autouse=True)
def reset_store():
    with store.lock:
        store.persons.clear()
        store.credentials.clear()
        store.payments.clear()
        store.nonces.clear()
        store.sessions.clear()
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
