import os

from src.config.settings import _normalize_database_url
from src.database.session import _build_sqlalchemy_url


def test_build_sqlalchemy_url_supports_relative_sqlite_path():
    result = _build_sqlalchemy_url("data/database.db")

    assert result == f"sqlite:///{os.path.abspath('data/database.db')}"


def test_build_sqlalchemy_url_supports_memory_sqlite():
    assert _build_sqlalchemy_url(":memory:") == "sqlite:///:memory:"


def test_normalize_database_url_supports_relative_sqlite_path():
    result = _normalize_database_url("data/database.db")

    assert result == f"sqlite:///{os.path.abspath('data/database.db')}"
