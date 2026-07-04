import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select

from app import create_app
from app import db as app_db
from app.models import Interaction, Person


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


def test_person_detail_shows_person_and_log_form(sqlite_app):
    with TestClient(sqlite_app()) as client:
        client.post(
            "/people",
            data={
                "name": "Ada Lovelace",
                "relationship": "Friend",
                "how_met": "Salon",
                "notes": "Ask about engines",
                "cadence_days": "14",
            },
        )
        person_id = _person_id_by_name("Ada Lovelace")
        resp = client.get(f"/people/{person_id}")

    assert resp.status_code == 200
    assert "Ada Lovelace" in resp.text
    assert "Friend" in resp.text
    assert "Salon" in resp.text
    assert "Ask about engines" in resp.text
    assert "14" in resp.text
    assert "Last contacted" in resp.text
    assert "never" in resp.text
    assert f'action="/people/{person_id}/interactions"' in resp.text
    assert 'name="note"' in resp.text
    assert 'name="at"' in resp.text


def test_post_interaction_redirects_and_appears_on_timeline(sqlite_app):
    with TestClient(sqlite_app()) as client:
        client.post("/people", data={"name": "Grace Hopper", "cadence_days": "28"})
        person_id = _person_id_by_name("Grace Hopper")
        post_resp = client.post(
            f"/people/{person_id}/interactions",
            data={"note": "Coffee catch-up", "at": "2026-07-02"},
            follow_redirects=False,
        )
        detail_resp = client.get(f"/people/{person_id}")

    assert post_resp.status_code == 303
    assert post_resp.headers["location"] == f"/people/{person_id}"
    assert detail_resp.status_code == 200
    assert "Coffee catch-up" in detail_resp.text
    assert "2026-07-02" in detail_resp.text
    assert "Last contacted" in detail_resp.text


def test_blank_note_rerenders_detail_without_creating_interaction(sqlite_app):
    with TestClient(sqlite_app()) as client:
        client.post("/people", data={"name": "Mary Jackson", "cadence_days": "28"})
        person_id = _person_id_by_name("Mary Jackson")
        resp = client.post(
            f"/people/{person_id}/interactions",
            data={"note": "   ", "at": "2026-07-02"},
        )
        with app_db.SessionLocal() as session:
            interactions = list(session.scalars(select(Interaction)))

    assert resp.status_code == 400
    assert "Note is required." in resp.text
    assert "Mary Jackson" in resp.text
    assert interactions == []


def test_last_contacted_uses_latest_interaction_and_timeline_is_newest_first(sqlite_app):
    with TestClient(sqlite_app()) as client:
        client.post("/people", data={"name": "Katherine Johnson", "cadence_days": "28"})
        person_id = _person_id_by_name("Katherine Johnson")
        client.post(
            f"/people/{person_id}/interactions",
            data={"note": "Older note", "at": "2026-06-01"},
        )
        client.post(
            f"/people/{person_id}/interactions",
            data={"note": "Newest note", "at": "2026-07-01"},
        )
        resp = client.get(f"/people/{person_id}")

    assert resp.status_code == 200
    assert "Last contacted" in resp.text
    assert "2026-07-01" in resp.text
    assert resp.text.index("Newest note") < resp.text.index("Older note")


def test_interaction_persists_across_app_reinstantiation(sqlite_app):
    with TestClient(sqlite_app()) as client:
        client.post("/people", data={"name": "Annie Easley", "cadence_days": "28"})
        person_id = _person_id_by_name("Annie Easley")
        client.post(
            f"/people/{person_id}/interactions",
            data={"note": "Restart-safe note", "at": "2026-07-01"},
        )

    with TestClient(sqlite_app()) as restarted_client:
        resp = restarted_client.get(f"/people/{person_id}")

    assert resp.status_code == 200
    assert "Annie Easley" in resp.text
    assert "Restart-safe note" in resp.text


def _person_id_by_name(name: str) -> int:
    with app_db.SessionLocal() as session:
        person_id = session.scalar(select(Person.id).where(Person.name == name))
    assert person_id is not None
    return person_id
