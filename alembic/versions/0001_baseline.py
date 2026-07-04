"""baseline

Revision ID: 0001
Revises: None
Create Date: 2026-07-04 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables() -> tuple[sa.Table, sa.Table]:
    metadata = sa.MetaData()
    person = sa.Table(
        "person",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("relationship", sa.Text(), nullable=True),
        sa.Column("how_met", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("cadence_days", sa.Integer(), nullable=False, server_default="28"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    interaction = sa.Table(
        "interaction",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("person_id", sa.Integer(), sa.ForeignKey("person.id"), nullable=False),
        sa.Column("at", sa.DateTime(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
    )
    return person, interaction


def upgrade() -> None:
    person, interaction = _tables()
    op.execute(sa.schema.CreateTable(person, if_not_exists=True))
    op.execute(sa.schema.CreateTable(interaction, if_not_exists=True))


def downgrade() -> None:
    person, interaction = _tables()
    op.execute(sa.schema.DropTable(interaction, if_exists=True))
    op.execute(sa.schema.DropTable(person, if_exists=True))
