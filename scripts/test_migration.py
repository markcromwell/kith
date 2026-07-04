from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def _alembic_config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_baseline_migration_creates_expected_tables(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)

    command.upgrade(_alembic_config(database_url), "head")
    command.upgrade(_alembic_config(database_url), "head")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        assert {"person", "interaction", "alembic_version"}.issubset(
            set(inspector.get_table_names())
        )

        person_columns = {column["name"] for column in inspector.get_columns("person")}
        assert {
            "id",
            "name",
            "relationship",
            "how_met",
            "notes",
            "cadence_days",
            "created_at",
        }.issubset(person_columns)

        interaction_columns = {
            column["name"] for column in inspector.get_columns("interaction")
        }
        assert {"id", "person_id", "at", "note"}.issubset(interaction_columns)
    finally:
        engine.dispose()
