from src.config.settings import Settings
from src.database.models import Proxy
from src.core.dynamic_proxy import fetch_dynamic_proxy
from src import proxy_utils
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


def test_proxy_model_url_injects_lsid_only_when_enabled(monkeypatch):
    monkeypatch.setattr(proxy_utils, "generate_proxy_lsid_token", lambda: "993523438")
    proxy = Proxy(
        name="demo",
        type="socks5",
        host="prem.us.iprocket.io",
        port=9595,
        username="com51844261-res-ROW-Lsid-TTL-600",
        password="HyDC8U451R8EWCt",
        lsid_enabled=True,
    )

    assert proxy.proxy_url == (
        "socks5h://com51844261-res-ROW-Lsid-993523438-TTL-600:"
        "HyDC8U451R8EWCt@prem.us.iprocket.io:9595"
    )


def test_settings_proxy_url_keeps_lsid_placeholder_when_switch_is_not_available(monkeypatch):
    monkeypatch.setattr(proxy_utils, "generate_proxy_lsid_token", lambda: "993523438")
    settings = Settings(
        proxy_enabled=True,
        proxy_type="socks5",
        proxy_host="prem.us.iprocket.io",
        proxy_port=9595,
        proxy_username="com51844261-res-ROW-Lsid-TTL-600",
        proxy_password="HyDC8U451R8EWCt",
    )

    assert settings.proxy_url == (
        "socks5h://com51844261-res-ROW-Lsid-TTL-600:"
        "HyDC8U451R8EWCt@prem.us.iprocket.io:9595"
    )


def test_proxy_model_url_keeps_generic_username_unchanged(monkeypatch):
    monkeypatch.setattr(proxy_utils, "generate_proxy_lsid_token", lambda: "993523438")
    proxy = Proxy(
        name="demo",
        type="socks5",
        host="127.0.0.1",
        port=1080,
        username="plain-user",
        password="secret",
        lsid_enabled=True,
    )

    assert proxy.proxy_url == "socks5h://plain-user:secret@127.0.0.1:1080"


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


def test_probe_proxy_connectivity_returns_exit_ip(monkeypatch):
    class DummyResponse:
        def __init__(self, status_code, payload=None, text=""):
            self.status_code = status_code
            self._payload = payload
            self.text = text

        def json(self):
            if self._payload is None:
                raise ValueError("no json")
            return self._payload

    calls = []

    class DummyRequests:
        @staticmethod
        def get(url, **kwargs):
            calls.append((url, kwargs))
            assert url == "https://api.ipify.org?format=json"
            return DummyResponse(200, payload={"ip": "1.2.3.4"})

    import sys

    monkeypatch.setitem(sys.modules, "curl_cffi", type("DummyCurlModule", (), {"requests": DummyRequests}))

    result = settings_routes._probe_proxy_connectivity("socks5://127.0.0.1:1080", timeout_seconds=2)

    assert result["success"] is True
    assert result["status_code"] == 200
    assert result["ip"] == "1.2.3.4"
    assert result["proxy_url"] == "socks5h://127.0.0.1:1080"
    assert result["message"] == "代理连接成功，出口 IP: 1.2.3.4"
    assert calls[0][1]["proxies"] == {
        "http": "socks5h://127.0.0.1:1080",
        "https": "socks5h://127.0.0.1:1080",
    }
