from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Person


router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


@router.get("/")
def home(request: Request, db: Annotated[Session, Depends(get_db)]):
    people = list(db.scalars(select(Person).order_by(func.lower(Person.name), Person.id)))
    return templates.TemplateResponse(request, "home.html", {"people": people})
