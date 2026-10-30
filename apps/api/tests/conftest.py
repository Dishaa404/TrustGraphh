import os

import pytest
from fastapi.testclient import TestClient
from eth_account import Account
from eth_account.messages import encode_defunct

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
        store.ngo_applications.clear()
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def login(client: TestClient, role: str = "donor", account=None) -> tuple[object, dict[str, str]]:
    account = account or Account.create()
    challenge = client.post("/auth/nonce", json={"wallet": account.address, "role": role}).json()
    signature = account.sign_message(encode_defunct(text=challenge["message"])).signature.hex()
    response = client.post("/auth/verify", json={"wallet": account.address, "role": role, "nonce": challenge["nonce"], "signature": signature})
    assert response.status_code == 200, response.text
    return account, {"Authorization": f"Bearer {response.json()['token']}"}
