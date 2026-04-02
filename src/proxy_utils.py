"""
代理协议辅助函数。

配置层保持 http / socks5 两种语义；
实际基于 curl_cffi 出网时，SOCKS5 默认升级为 socks5h，
避免目标域名在本地解析导致连通性异常。
"""

from __future__ import annotations

import secrets
import string
import re
from typing import Optional
from urllib.parse import quote, urlsplit, urlunsplit


def normalize_proxy_type(proxy_type: Optional[str]) -> str:
    """将代理类型归一化到持久化层支持的协议集合。"""
    value = str(proxy_type or "http").strip().lower()
    if value in {"http", "https"}:
        return "http"
    if value in {"socks", "socks5", "socks5h"}:
        return "socks5"
    return "http"


def build_proxy_url(
    proxy_type: Optional[str],
    host: Optional[str],
    port: Optional[int],
    username: Optional[str] = None,
    password: Optional[str] = None,
    enable_lsid: bool = False,
) -> Optional[str]:
    """生成供 HTTP 客户端直接使用的代理 URL。"""
    normalized_type = normalize_proxy_type(proxy_type)
    host_value = str(host or "").strip()
    if not host_value:
        return None

    try:
        port_value = int(port or 0)
    except (TypeError, ValueError):
        return None
    if port_value <= 0:
        return None

    if ":" in host_value and not host_value.startswith("["):
        host_value = f"[{host_value}]"

    scheme = "http" if normalized_type == "http" else "socks5"

    auth = ""
    if username is not None or password is not None:
        runtime_username = inject_proxy_username_lsid(username) if enable_lsid else username
        auth = quote(str(runtime_username or ""), safe="")
        if password is not None:
            auth += f":{quote(str(password or ''), safe='')}"
        auth += "@"

    return upgrade_proxy_url_for_requests(f"{scheme}://{auth}{host_value}:{port_value}")


def upgrade_proxy_url_for_requests(proxy_url: Optional[str]) -> Optional[str]:
    """将原始代理 URL 调整为请求层使用的协议。"""
    text = str(proxy_url or "").strip()
    if not text:
        return None

    lower = text.lower()
    if lower.startswith("socks5h://"):
        return text
    if lower.startswith("socks5://"):
        return f"socks5h://{text[9:]}"
    if lower.startswith("socks://"):
        return f"socks5h://{text[8:]}"
    return text


def generate_proxy_lsid_token() -> str:
    """生成 9 位 Lsid，首位必须为 8 或 9。"""
    return secrets.choice("89") + "".join(secrets.choice(string.digits) for _ in range(8))


def inject_proxy_username_lsid(username: Optional[str], token: Optional[str] = None) -> Optional[str]:
    """
    为代理用户名注入或刷新 Lsid-9位随机数。

    示例：
    com51844261-res-ROW-Lsid-TTL-600
    -> com51844261-res-ROW-Lsid-993523438-TTL-600
    """
    text = str(username or "").strip()
    if not text:
        return username
    if "Lsid" not in text:
        return username

    lsid_token = str(token or generate_proxy_lsid_token()).strip()
    updated = re.sub(r"Lsid(?:-\d{9})?", f"Lsid-{lsid_token}", text, count=1)
    return updated


def build_registration_proxy_url(
    proxy_url: Optional[str],
    token: Optional[str] = None,
    enable_lsid: bool = False,
) -> Optional[str]:
    """
    仅在注册链路使用的运行时代理 URL。

    仅在显式启用时，为代理用户名注入/刷新 Lsid-9位随机数；
    同时保持既有 socks5 -> socks5h 的请求层升级逻辑。
    """
    runtime_proxy = upgrade_proxy_url_for_requests(proxy_url)
    if not runtime_proxy or not enable_lsid:
        return runtime_proxy

    parsed = urlsplit(runtime_proxy)
    if not parsed.scheme or parsed.hostname is None or parsed.username is None:
        return runtime_proxy

    username = inject_proxy_username_lsid(parsed.username, token=token)
    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"

    auth = quote(str(username or ""), safe="")
    if parsed.password is not None:
        auth += f":{quote(parsed.password, safe='')}"

    netloc = f"{auth}@{host}"
    if parsed.port:
        netloc += f":{parsed.port}"

    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
