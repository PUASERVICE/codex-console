"""
代理协议辅助函数。

配置层保持 http / socks5 两种语义；
实际基于 curl_cffi 出网时，SOCKS5 默认升级为 socks5h，
避免目标域名在本地解析导致连通性异常。
"""

from __future__ import annotations

from typing import Optional
from urllib.parse import quote


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

    scheme = "http" if normalized_type == "http" else "socks5h"

    auth = ""
    if username is not None or password is not None:
        auth = quote(str(username or ""), safe="")
        if password is not None:
            auth += f":{quote(str(password or ''), safe='')}"
        auth += "@"

    return f"{scheme}://{auth}{host_value}:{port_value}"


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
