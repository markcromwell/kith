from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select

from app import create_app
from app import db as app_db
from app.models import Interaction, Person
from app.overdue import compute_overdue


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
    assert 'href="/people"' in resp.text
    assert 'href="/people/new"' in resp.text


def test_health_ok_exact_body():
    with TestClient(create_app()) as client:
        resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_compute_overdue_filters_ranks_and_labels_with_fixed_now():
    now = datetime(2026, 7, 4, 12, 0)
    oldest = Person(id=1, name="Oldest", cadence_days=14, created_at=datetime(2026, 1, 1))
    oldest.interactions = [Interaction(at=datetime(2026, 5, 1))]
    recent = Person(id=2, name="Recent", cadence_days=28, created_at=datetime(2026, 1, 1))
    recent.interactions = [Interaction(at=datetime(2026, 6, 20))]
    never = Person(id=3, name="Never", cadence_days=0, created_at=datetime(2026, 6, 20))
    never.interactions = []
    less_than_week = Person(
        id=4,
        name="Less Than Week",
        cadence_days=28,
        created_at=datetime(2026, 1, 1),
    )
    less_than_week.interactions = [Interaction(at=datetime(2026, 6, 1))]

    overdue = compute_overdue([recent, never, less_than_week, oldest], now=now)

    assert [item.person.name for item in overdue] == ["Oldest", "Never", "Less Than Week"]
    assert [item.label for item in overdue] == [
        "7 weeks overdue",
        "2 weeks overdue",
        "5 days overdue",
    ]


def test_home_lists_only_overdue_people_ranked_with_labels(sqlite_app):
    with TestClient(sqlite_app()) as client:
        _add_person_with_interaction(
            "More Overdue",
            cadence_days=14,
            created_at=datetime(2026, 1, 1),
            interaction_at=datetime(2026, 5, 1),
        )
        _add_person_with_interaction(
            "Less Overdue",
            cadence_days=28,
            created_at=datetime(2026, 1, 1),
            interaction_at=datetime(2026, 6, 1),
        )
        _add_person_with_interaction(
            "Within Cadence",
            cadence_days=28,
            created_at=datetime(2026, 1, 1),
            interaction_at=datetime(2026, 6, 20),
        )
        with patch("app.routers.home._current_time", return_value=datetime(2026, 7, 4, 12, 0)):
            resp = client.get("/")

    assert resp.status_code == 200
    assert resp.text.index("More Overdue") < resp.text.index("Less Overdue")
    assert "7 weeks overdue" in resp.text
    assert "5 days overdue" in resp.text
    assert "Within Cadence" not in resp.text
    assert 'action="/people/' in resp.text
    assert '/reached-out" method="post"' in resp.text
    assert 'href="/people/new"' in resp.text
    assert 'href="/people"' in resp.text


def test_home_shows_never_contacted_person_as_overdue(sqlite_app):
    with TestClient(sqlite_app()) as client:
        _add_person("Never Contacted", cadence_days=14, created_at=datetime(2026, 5, 1))
        with patch("app.routers.home._current_time", return_value=datetime(2026, 7, 4, 12, 0)):
            resp = client.get("/")

    assert resp.status_code == 200
    assert "Never Contacted" in resp.text
    assert "7 weeks overdue" in resp.text


def test_home_empty_when_nobody_overdue(sqlite_app):
    with TestClient(sqlite_app()) as client:
        _add_person_with_interaction(
            "Caught Up",
            cadence_days=28,
            created_at=datetime(2026, 1, 1),
            interaction_at=datetime(2026, 6, 20),
        )
        with patch("app.routers.home._current_time", return_value=datetime(2026, 7, 4, 12, 0)):
            resp = client.get("/")

    assert resp.status_code == 200
    assert "No one to reach out to yet" in resp.text
    assert "Caught Up" not in resp.text


def test_mark_reached_out_logs_interaction_redirects_and_drops_from_home(sqlite_app):
    now = datetime(2026, 7, 4, 12, 0)
    with TestClient(sqlite_app()) as client:
        person_id = _add_person_with_interaction(
            "Reach Out",
            cadence_days=14,
            created_at=datetime(2026, 1, 1),
            interaction_at=datetime(2026, 5, 1),
        )
        with patch("app.routers.home._current_time", return_value=now):
            post_resp = client.post(f"/people/{person_id}/reached-out", follow_redirects=False)
            home_resp = client.get("/")
        interactions = _interactions_for_person(person_id)

    assert post_resp.status_code == 303
    assert post_resp.headers["location"] == "/"
    assert len(interactions) == 2
    assert interactions[-1].at == now
    assert interactions[-1].note == "Reached out"
    assert home_resp.status_code == 200
    assert "Reach Out" not in home_resp.text
    assert "No one to reach out to yet" in home_resp.text


def test_mark_reached_out_unknown_person_404(sqlite_app):
    with TestClient(sqlite_app()) as client:
        resp = client.post("/people/999/reached-out", follow_redirects=False)

    assert resp.status_code == 404


def _add_person(name: str, cadence_days: int, created_at: datetime) -> int:
    with app_db.SessionLocal() as session:
        person = Person(name=name, cadence_days=cadence_days, created_at=created_at)
        session.add(person)
        session.commit()
        return person.id


def _add_person_with_interaction(
    name: str,
    cadence_days: int,
    created_at: datetime,
    interaction_at: datetime,
) -> int:
    with app_db.SessionLocal() as session:
        person = Person(name=name, cadence_days=cadence_days, created_at=created_at)
        session.add(person)
        session.flush()
        session.add(Interaction(person_id=person.id, at=interaction_at, note="Old note"))
        session.commit()
        return person.id


def _interactions_for_person(person_id: int) -> list[Interaction]:
    with app_db.SessionLocal() as session:
        return list(
            session.scalars(
                select(Interaction)
                .where(Interaction.person_id == person_id)
                .order_by(Interaction.at, Interaction.id)
            )
        )
