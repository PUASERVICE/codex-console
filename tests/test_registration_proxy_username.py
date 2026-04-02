from src.proxy_utils import (
    build_registration_proxy_url,
    inject_proxy_username_lsid,
)


def test_inject_proxy_username_lsid_replaces_placeholder():
    result = inject_proxy_username_lsid(
        "com51844261-res-ROW-Lsid-TTL-600",
        token="993523438",
    )

    assert result == "com51844261-res-ROW-Lsid-993523438-TTL-600"


def test_inject_proxy_username_lsid_replaces_existing_digits():
    result = inject_proxy_username_lsid(
        "com51844261-res-ROW-Lsid-812345678-TTL-600",
        token="901234567",
    )

    assert result == "com51844261-res-ROW-Lsid-901234567-TTL-600"


def test_build_registration_proxy_url_updates_username_and_keeps_socks5h():
    result = build_registration_proxy_url(
        "socks5://com51844261-res-ROW-Lsid-TTL-600:HyDC8U451R8EWCt@prem.us.iprocket.io:9595",
        token="993523438",
        enable_lsid=True,
    )

    assert result == (
        "socks5h://com51844261-res-ROW-Lsid-993523438:HyDC8U451R8EWCt@prem.us.iprocket.io:9595"
    ).replace(
        "ROW-Lsid-993523438:",
        "ROW-Lsid-993523438-TTL-600:"
    )


def test_build_registration_proxy_url_without_username_is_unchanged():
    result = build_registration_proxy_url(
        "socks5://127.0.0.1:1080",
        token="993523438",
        enable_lsid=True,
    )

    assert result == "socks5h://127.0.0.1:1080"


def test_build_registration_proxy_url_keeps_username_unchanged_when_lsid_disabled():
    result = build_registration_proxy_url(
        "socks5://com51844261-res-ROW-Lsid-TTL-600:HyDC8U451R8EWCt@prem.us.iprocket.io:9595",
        token="993523438",
        enable_lsid=False,
    )

    assert result == (
        "socks5h://com51844261-res-ROW-Lsid-TTL-600:"
        "HyDC8U451R8EWCt@prem.us.iprocket.io:9595"
    )


def test_inject_proxy_username_lsid_keeps_generic_username_unchanged():
    result = inject_proxy_username_lsid(
        "plain-user",
        token="993523438",
    )

    assert result == "plain-user"
