from src.core.upload import tokensolo_upload


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json payload")
        return self._payload


class DummyAccount:
    def __init__(self, account_id="acct_123", email="tester@example.com", access_token="token_abc"):
        self.account_id = account_id
        self.email = email
        self.access_token = access_token


def test_build_tokensolo_import_url_accepts_root_url():
    assert (
        tokensolo_upload.build_tokensolo_import_url("https://tokensolo.com", channel="codex")
        == "https://tokensolo.com/api/channel/codex/import"
    )


def test_build_tokensolo_import_url_keeps_full_import_endpoint():
    assert (
        tokensolo_upload.build_tokensolo_import_url("https://tokensolo.com/api/channel/codex/import", channel="codex")
        == "https://tokensolo.com/api/channel/codex/import"
    )


def test_upload_to_tokensolo_posts_expected_payload(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append({"url": url, "kwargs": kwargs})
        return FakeResponse(status_code=201)

    monkeypatch.setattr(tokensolo_upload.cffi_requests, "post", fake_post)

    success, message = tokensolo_upload.upload_to_tokensolo(
        [DummyAccount()],
        api_url="https://tokensolo.com",
        import_secret="secret-123",
        channel="codex",
        account_type="codex",
        models="gpt-5.4,gpt-5.2",
    )

    assert success is True
    assert "成功上传 1 个账号" in message
    assert calls[0]["url"] == "https://tokensolo.com/api/channel/codex/import"
    assert calls[0]["kwargs"]["headers"]["X-Codex-Import-Secret"] == "secret-123"
    assert calls[0]["kwargs"]["json"]["payload"][0]["models"] == ["gpt-5.4", "gpt-5.2"]


def test_test_tokensolo_connection_treats_400_as_reachable(monkeypatch):
    def fake_post(url, **kwargs):
        return FakeResponse(status_code=400, payload={"error": "payload required"})

    monkeypatch.setattr(tokensolo_upload.cffi_requests, "post", fake_post)

    success, message = tokensolo_upload.test_tokensolo_connection(
        "https://tokensolo.com/api/channel/codex/import",
        "secret-123",
        channel="codex",
    )

    assert success is True
    assert message == "TokenSolo 连接测试成功"
