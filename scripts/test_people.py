import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select

from app import create_app
from app import db as app_db
from app.models import Person


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


def test_new_person_form_renders(sqlite_app):
    with TestClient(sqlite_app()) as client:
        resp = client.get("/people/new")

    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "<form" in resp.text
    assert 'name="name"' in resp.text
    assert 'name="relationship"' in resp.text
    assert 'name="how_met"' in resp.text
    assert 'name="notes"' in resp.text
    assert 'name="cadence_days"' in resp.text
    assert 'value="28"' in resp.text


def test_create_person_then_list_shows_person(sqlite_app):
    with TestClient(sqlite_app()) as client:
        create_resp = client.post(
            "/people",
            data={"name": "Ada Lovelace", "relationship": "Friend", "cadence_days": "14"},
            follow_redirects=False,
        )
        list_resp = client.get("/people")

    assert create_resp.status_code == 303
    assert create_resp.headers["location"] == "/people"
    assert list_resp.status_code == 200
    assert "Ada Lovelace" in list_resp.text
    assert "Friend" in list_resp.text
    assert "14" in list_resp.text
    assert "never" in list_resp.text


def test_people_list_shows_last_contacted_label(sqlite_app):
    with TestClient(sqlite_app()) as client:
        client.post("/people", data={"name": "Dorothy Vaughan", "cadence_days": "28"})
        person_id = _person_id_by_name("Dorothy Vaughan")
        never_resp = client.get("/people")
        client.post(
            f"/people/{person_id}/interactions",
            data={"note": "Sent a letter", "at": "2026-07-03"},
        )
        contacted_resp = client.get("/people")

    assert never_resp.status_code == 200
    assert "Dorothy Vaughan" in never_resp.text
    assert "never" in never_resp.text
    assert contacted_resp.status_code == 200
    assert "last contacted 1 day ago" in contacted_resp.text


def test_missing_name_rerenders_form_without_creating_person(sqlite_app):
    with TestClient(sqlite_app()) as client:
        resp = client.post(
            "/people",
            data={"name": "", "relationship": "Friend", "cadence_days": "28"},
        )
        with app_db.SessionLocal() as session:
            people = list(session.scalars(select(Person)))

    assert resp.status_code == 400
    assert "Name is required." in resp.text
    assert "<form" in resp.text
    assert people == []


def test_person_persists_across_app_reinstantiation(sqlite_app):
    with TestClient(sqlite_app()) as client:
        client.post("/people", data={"name": "Grace Hopper", "cadence_days": "28"})

    with TestClient(sqlite_app()) as restarted_client:
        resp = restarted_client.get("/people")

    assert resp.status_code == 200
    assert "Grace Hopper" in resp.text


def test_edit_updates_person_field(sqlite_app):
    with TestClient(sqlite_app()) as client:
        client.post(
            "/people",
            data={
                "name": "Katherine Johnson",
                "relationship": "Colleague",
                "how_met": "Work",
                "notes": "Math",
                "cadence_days": "21",
            },
        )
        list_resp = client.get("/people")
        person_id = _person_id_by_name("Katherine Johnson")
        edit_resp = client.get(f"/people/{person_id}/edit")
        update_resp = client.post(
            f"/people/{person_id}",
            data={
                "name": "Katherine Johnson",
                "relationship": "Mentor",
                "how_met": "Conference",
                "notes": "Orbital mechanics",
                "cadence_days": "7",
            },
            follow_redirects=False,
        )
        updated_list_resp = client.get("/people")

    assert "Katherine Johnson" in list_resp.text
    assert edit_resp.status_code == 200
    assert 'value="Katherine Johnson"' in edit_resp.text
    assert 'value="Colleague"' in edit_resp.text
    assert 'value="Work"' in edit_resp.text
    assert "Math" in edit_resp.text
    assert 'value="21"' in edit_resp.text
    assert update_resp.status_code == 303
    assert update_resp.headers["location"] == "/people"
    assert "Mentor" in updated_list_resp.text
    assert "7" in updated_list_resp.text
    assert "Colleague" not in updated_list_resp.text


def test_delete_removes_person(sqlite_app):
    with TestClient(sqlite_app()) as client:
        client.post("/people", data={"name": "Mary Jackson", "cadence_days": "28"})
        person_id = _person_id_by_name("Mary Jackson")
        delete_resp = client.post(f"/people/{person_id}/delete", follow_redirects=False)
        list_resp = client.get("/people")

    assert delete_resp.status_code == 303
    assert delete_resp.headers["location"] == "/people"
    assert "Mary Jackson" not in list_resp.text


def test_unknown_person_routes_return_404(sqlite_app):
    with TestClient(sqlite_app()) as client:
        edit_resp = client.get("/people/999/edit")
        update_resp = client.post("/people/999", data={"name": "Nobody"})
        delete_resp = client.post("/people/999/delete")

    assert edit_resp.status_code == 404
    assert update_resp.status_code == 404
    assert delete_resp.status_code == 404


def _person_id_by_name(name: str) -> int:
    with app_db.SessionLocal() as session:
        person_id = session.scalar(select(Person.id).where(Person.name == name))
    assert person_id is not None
    return person_id
