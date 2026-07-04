from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Person


router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


def _ordered_people(db: Session) -> list[Person]:
    return list(db.scalars(select(Person).order_by(func.lower(Person.name), Person.id)))


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


@router.get("/people")
def people_list(request: Request, db: Annotated[Session, Depends(get_db)]):
    return templates.TemplateResponse(
        request,
        "people_list.html",
        {"people": _ordered_people(db)},
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
