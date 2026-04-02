from src.config.settings import Settings
from src.database.models import Proxy
from src.core.dynamic_proxy import fetch_dynamic_proxy
from src.web.routes import settings as settings_routes


def test_settings_proxy_url_upgrades_socks5_to_socks5h():
    settings = Settings(
        proxy_enabled=True,
        proxy_type="socks5",
        proxy_host="127.0.0.1",
        proxy_port=1080,
    )

    assert settings.proxy_url == "socks5h://127.0.0.1:1080"


def test_proxy_model_url_upgrades_socks5_to_socks5h():
    proxy = Proxy(
        name="demo",
        type="socks5",
        host="127.0.0.1",
        port=1080,
    )

    assert proxy.proxy_url == "socks5h://127.0.0.1:1080"


def test_normalize_proxy_type_maps_socks5h_back_to_socks5():
    assert settings_routes._normalize_proxy_type("socks5h") == "socks5"


def test_fetch_dynamic_proxy_upgrades_socks5_scheme(monkeypatch):
    class DummyResponse:
        status_code = 200
        text = "socks5://127.0.0.1:1080"

    class DummyRequests:
        @staticmethod
        def get(*args, **kwargs):
            return DummyResponse()

    import sys

    monkeypatch.setitem(sys.modules, "curl_cffi", type("DummyCurlModule", (), {"requests": DummyRequests}))

    proxy_url = fetch_dynamic_proxy("http://proxy-provider.example/api")

    assert proxy_url == "socks5h://127.0.0.1:1080"


def test_probe_proxy_connectivity_accepts_openai_reachable_status(monkeypatch):
    class DummyResponse:
        def __init__(self, status_code):
            self.status_code = status_code

    calls = []

    class DummyRequests:
        @staticmethod
        def get(url, **kwargs):
            calls.append((url, kwargs))
            if url == "https://chatgpt.com/backend-api/me":
                return DummyResponse(401)
            raise AssertionError(f"unexpected url: {url}")

    import sys

    monkeypatch.setitem(sys.modules, "curl_cffi", type("DummyCurlModule", (), {"requests": DummyRequests}))

    result = settings_routes._probe_proxy_connectivity("socks5://127.0.0.1:1080", timeout_seconds=2)

    assert result["success"] is True
    assert result["status_code"] == 401
    assert result["proxy_url"] == "socks5h://127.0.0.1:1080"
    assert calls[0][1]["proxy"] == "socks5h://127.0.0.1:1080"
