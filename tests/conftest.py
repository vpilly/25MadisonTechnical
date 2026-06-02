import sys
import os
import pytest

# Make src/ and tests/ both importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))


@pytest.fixture
def db(tmp_path, monkeypatch):
    """
    Patch DATABASE_PATH to a fresh temp file and initialise the schema.
    Reverts automatically after each test via monkeypatch.
    """
    import database
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(database, "DATABASE_PATH", db_path)
    database.init_db()
    return db_path
