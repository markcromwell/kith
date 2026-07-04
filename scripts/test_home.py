from fastapi.testclient import TestClient

from app import create_app


def test_home_empty_state_html():
    with TestClient(create_app()) as client:
        resp = client.get("/")

    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "No one to reach out to yet" in resp.text


def test_health_ok_exact_body():
    with TestClient(create_app()) as client:
        resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
