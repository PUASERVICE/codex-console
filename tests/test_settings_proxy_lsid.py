import asyncio
from contextlib import contextmanager

from src.database import crud
from src.database.session import DatabaseSessionManager
from src.web.routes import settings as settings_routes


def _build_manager(tmp_path):
    db_path = tmp_path / "settings_proxy_lsid.db"
    manager = DatabaseSessionManager(f"sqlite:///{db_path}")
    manager.create_tables()
    manager.migrate_tables()
    return manager


def test_update_proxy_item_persists_lsid_enabled(monkeypatch, tmp_path):
    manager = _build_manager(tmp_path)

    @contextmanager
    def fake_get_db():
        session = manager.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    monkeypatch.setattr(settings_routes, "get_db", fake_get_db)

    with manager.SessionLocal() as session:
        proxy = crud.create_proxy(
            session,
            name="demo",
            type="socks5",
            host="127.0.0.1",
            port=1080,
            username="com51844261-res-ROW-Lsid-TTL-600",
            password="secret",
            lsid_enabled=False,
        )
        proxy_id = proxy.id

    result = asyncio.run(
        settings_routes.update_proxy_item(
            proxy_id,
            settings_routes.ProxyUpdateRequest(lsid_enabled=True),
        )
    )

    assert result["success"] is True
    assert result["proxy"]["lsid_enabled"] is True

    fetched = asyncio.run(settings_routes.get_proxy_item(proxy_id))
    assert fetched["lsid_enabled"] is True


def test_get_proxies_list_exposes_lsid_enabled(monkeypatch, tmp_path):
    manager = _build_manager(tmp_path)

    @contextmanager
    def fake_get_db():
        session = manager.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    monkeypatch.setattr(settings_routes, "get_db", fake_get_db)

    with manager.SessionLocal() as session:
        crud.create_proxy(
            session,
            name="demo",
            type="socks5",
            host="127.0.0.1",
            port=1080,
            username="com51844261-res-ROW-Lsid-TTL-600",
            password="secret",
            lsid_enabled=True,
        )

    payload = asyncio.run(settings_routes.get_proxies_list())
    assert payload["total"] == 1
    assert payload["proxies"][0]["lsid_enabled"] is True
