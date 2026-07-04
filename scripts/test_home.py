import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app import create_app
from app import db as app_db


@pytest.fixture
def sqlite_app(tmp_path):
    original_engine = app_db.engine
    test_engine = create_engine(
        f"sqlite:///{tmp_path / 'kith.db'}",
        connect_args={"check_same_thread": False},
    )
    app_db.engine = test_engine
    app_db.SessionLocal.configure(bind=test_engine)
    try:
        yield create_app
    finally:
        app_db.SessionLocal.configure(bind=original_engine)
        app_db.engine = original_engine
        test_engine.dispose()


def test_home_empty_state_html(sqlite_app):
    with TestClient(sqlite_app()) as client:
        resp = client.get("/")

    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "No one to reach out to yet" in resp.text


def test_health_ok_exact_body():
    with TestClient(create_app()) as client:
        resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_home_lists_people_and_add_link(sqlite_app):
    with TestClient(sqlite_app()) as client:
        client.post("/people", data={"name": "Ada Lovelace", "cadence_days": "28"})
        resp = client.get("/")

    assert resp.status_code == 200
    assert "Ada Lovelace" in resp.text
    assert 'href="/people/new"' in resp.text
    assert "Add someone" in resp.text
