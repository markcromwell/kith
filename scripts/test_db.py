from sqlalchemy import create_engine, inspect

from app import db


def test_init_sqlite_schema_creates_tables_and_is_idempotent(tmp_path):
    test_engine = create_engine(f"sqlite:///{tmp_path / 'kith.db'}")
    original_engine = db.engine
    db.engine = test_engine
    try:
        db.init_sqlite_schema()
        db.init_sqlite_schema()

        inspector = inspect(test_engine)
        assert {"person", "interaction"}.issubset(set(inspector.get_table_names()))
    finally:
        db.engine = original_engine
        test_engine.dispose()
