from fastapi.testclient import TestClient

from docs_copilot.api.app import create_app

client = TestClient(create_app())


def test_healthz() -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_readyz() -> None:
    assert client.get("/readyz").status_code == 200
