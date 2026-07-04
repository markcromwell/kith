from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import Interaction, Person
from app.overdue import compute_overdue


router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


def _current_time() -> datetime:
    return datetime.now()


@router.get("/")
def home(request: Request, db: Annotated[Session, Depends(get_db)]):
    people = list(
        db.scalars(
            select(Person)
            .options(selectinload(Person.interactions))
            .order_by(func.lower(Person.name), Person.id)
        )
    )
    return templates.TemplateResponse(
        request,
        "home.html",
        {"overdue_people": compute_overdue(people, now=_current_time())},
    )


@router.post("/people/{person_id}/reached-out")
def mark_reached_out(person_id: int, db: Annotated[Session, Depends(get_db)]):
    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404)

    db.add(
        Interaction(
            person_id=person.id,
            at=_current_time(),
            note="Reached out",
        )
    )
    db.commit()
    return RedirectResponse("/", status_code=303)
