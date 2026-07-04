from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from app.models import Person


@dataclass(frozen=True)
class OverduePerson:
    person: Person
    label: str
    days_overdue: int


def compute_overdue(people: Iterable[Person], now: datetime) -> list[OverduePerson]:
    overdue_people: list[OverduePerson] = []

    for person in people:
        last_contacted = _last_contacted(person)
        days_since_contact = (now - last_contacted).days
        excess_days = days_since_contact - person.cadence_days
        if excess_days <= 0:
            continue

        overdue_people.append(
            OverduePerson(
                person=person,
                label=_overdue_label(excess_days),
                days_overdue=excess_days,
            )
        )

    return sorted(
        overdue_people,
        key=lambda item: (-item.days_overdue, item.person.name.lower(), item.person.id or 0),
    )


def _last_contacted(person: Person) -> datetime:
    if person.interactions:
        return max(interaction.at for interaction in person.interactions)
    return person.created_at


def _overdue_label(excess_days: int) -> str:
    if excess_days < 7:
        unit = "day" if excess_days == 1 else "days"
        return f"{excess_days} {unit} overdue"

    weeks = excess_days // 7
    unit = "week" if weeks == 1 else "weeks"
    return f"{weeks} {unit} overdue"
