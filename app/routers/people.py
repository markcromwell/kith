from datetime import date, datetime, time
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Interaction, Person


router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


def _ordered_people(db: Session) -> list[Person]:
    return list(db.scalars(select(Person).order_by(func.lower(Person.name), Person.id)))


def _last_contacted_by_person_id(db: Session) -> dict[int, datetime]:
    rows = db.execute(
        select(Interaction.person_id, func.max(Interaction.at)).group_by(Interaction.person_id)
    )
    return {
        person_id: _coerce_datetime(last_contacted)
        for person_id, last_contacted in rows
        if last_contacted
    }


def _last_contacted_label(last_contacted: datetime | None) -> str:
    if last_contacted is None:
        return "never"

    days_ago = (date.today() - last_contacted.date()).days
    if days_ago == 0:
        return "last contacted today"
    if days_ago == 1:
        return "last contacted 1 day ago"
    return f"last contacted {days_ago} days ago"


def _person_interactions(db: Session, person_id: int) -> list[Interaction]:
    return list(
        db.scalars(
            select(Interaction)
            .where(Interaction.person_id == person_id)
            .order_by(Interaction.at.desc(), Interaction.id.desc())
        )
    )


def _person_last_contacted(db: Session, person_id: int) -> datetime | None:
    last_contacted = db.scalar(
        select(func.max(Interaction.at)).where(Interaction.person_id == person_id)
    )
    if last_contacted is None:
        return None
    return _coerce_datetime(last_contacted)


def _coerce_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _parse_interaction_at(value: str | None) -> datetime:
    if value is None or value.strip() == "":
        return datetime.now()
    return datetime.combine(date.fromisoformat(value.strip()), time.min)


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _cadence_days(value: str | None) -> int:
    if value is None or value.strip() == "":
        return 28
    return int(value)


def _form_person(
    name: str | None,
    relationship: str | None,
    how_met: str | None,
    notes: str | None,
    cadence_days: str | None,
) -> dict[str, object]:
    return {
        "name": name or "",
        "relationship": relationship or "",
        "how_met": how_met or "",
        "notes": notes or "",
        "cadence_days": cadence_days or "28",
    }


def _form_error_response(
    request: Request,
    action: str,
    person: Person | dict[str, object] | None,
    message: str,
):
    return templates.TemplateResponse(
        request,
        "people_form.html",
        {
            "action": action,
            "person": person,
            "error": message,
        },
        status_code=400,
    )


def _person_detail_response(
    request: Request,
    db: Session,
    person: Person,
    error: str | None = None,
    status_code: int = 200,
):
    last_contacted = _person_last_contacted(db, person.id)
    return templates.TemplateResponse(
        request,
        "person_detail.html",
        {
            "person": person,
            "interactions": _person_interactions(db, person.id),
            "last_contacted": last_contacted,
            "error": error,
        },
        status_code=status_code,
    )


@router.get("/people")
def people_list(request: Request, db: Annotated[Session, Depends(get_db)]):
    people = _ordered_people(db)
    last_contacted_by_person_id = _last_contacted_by_person_id(db)
    return templates.TemplateResponse(
        request,
        "people_list.html",
        {
            "people": people,
            "last_contacted_labels": {
                person.id: _last_contacted_label(last_contacted_by_person_id.get(person.id))
                for person in people
            },
        },
    )


@router.get("/people/new")
def new_person(request: Request):
    return templates.TemplateResponse(
        request,
        "people_form.html",
        {
            "action": "/people",
            "person": {"cadence_days": 28},
            "error": None,
        },
    )


@router.get("/people/{person_id}")
def person_detail(request: Request, person_id: int, db: Annotated[Session, Depends(get_db)]):
    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404)

    return _person_detail_response(request, db, person)


@router.post("/people")
def create_person(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    name: Annotated[str | None, Form()] = None,
    relationship: Annotated[str | None, Form()] = None,
    how_met: Annotated[str | None, Form()] = None,
    notes: Annotated[str | None, Form()] = None,
    cadence_days: Annotated[str | None, Form()] = None,
):
    if not name or not name.strip():
        return _form_error_response(
            request,
            "/people",
            _form_person(name, relationship, how_met, notes, cadence_days),
            "Name is required.",
        )

    try:
        parsed_cadence_days = _cadence_days(cadence_days)
    except ValueError:
        return _form_error_response(
            request,
            "/people",
            _form_person(name, relationship, how_met, notes, cadence_days),
            "Cadence days must be an integer.",
        )

    db.add(
        Person(
            name=name.strip(),
            relationship=_clean_optional(relationship),
            how_met=_clean_optional(how_met),
            notes=_clean_optional(notes),
            cadence_days=parsed_cadence_days,
        )
    )
    db.commit()
    return RedirectResponse("/people", status_code=303)


@router.post("/people/{person_id}/interactions")
def create_interaction(
    request: Request,
    person_id: int,
    db: Annotated[Session, Depends(get_db)],
    note: Annotated[str | None, Form()] = None,
    at: Annotated[str | None, Form()] = None,
):
    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404)
    if not note or not note.strip():
        return _person_detail_response(
            request,
            db,
            person,
            error="Note is required.",
            status_code=400,
        )

    try:
        parsed_at = _parse_interaction_at(at)
    except ValueError:
        return _person_detail_response(
            request,
            db,
            person,
            error="Interaction date must be a valid date.",
            status_code=400,
        )

    db.add(Interaction(person_id=person.id, at=parsed_at, note=note.strip()))
    db.commit()
    return RedirectResponse(f"/people/{person.id}", status_code=303)


@router.get("/people/{person_id}/edit")
def edit_person(request: Request, person_id: int, db: Annotated[Session, Depends(get_db)]):
    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404)

    return templates.TemplateResponse(
        request,
        "people_form.html",
        {
            "action": f"/people/{person.id}",
            "person": person,
            "error": None,
        },
    )


@router.post("/people/{person_id}")
def update_person(
    request: Request,
    person_id: int,
    db: Annotated[Session, Depends(get_db)],
    name: Annotated[str | None, Form()] = None,
    relationship: Annotated[str | None, Form()] = None,
    how_met: Annotated[str | None, Form()] = None,
    notes: Annotated[str | None, Form()] = None,
    cadence_days: Annotated[str | None, Form()] = None,
):
    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404)
    if not name or not name.strip():
        return _form_error_response(
            request,
            f"/people/{person.id}",
            _form_person(name, relationship, how_met, notes, cadence_days),
            "Name is required.",
        )

    try:
        parsed_cadence_days = _cadence_days(cadence_days)
    except ValueError:
        return _form_error_response(
            request,
            f"/people/{person.id}",
            _form_person(name, relationship, how_met, notes, cadence_days),
            "Cadence days must be an integer.",
        )

    person.name = name.strip()
    person.relationship = _clean_optional(relationship)
    person.how_met = _clean_optional(how_met)
    person.notes = _clean_optional(notes)
    person.cadence_days = parsed_cadence_days
    db.commit()
    return RedirectResponse("/people", status_code=303)


@router.post("/people/{person_id}/delete")
def delete_person(person_id: int, db: Annotated[Session, Depends(get_db)]):
    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404)

    db.delete(person)
    db.commit()
    return RedirectResponse("/people", status_code=303)
