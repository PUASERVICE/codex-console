"""
TokenSolo 账号上传功能
"""

import logging
from typing import Iterable, List, Optional, Sequence, Tuple

from curl_cffi import requests as cffi_requests

from ...database.models import Account
from ...database.session import get_db

logger = logging.getLogger(__name__)

DEFAULT_TOKENSOLO_CHANNEL = "codex"
DEFAULT_TOKENSOLO_ACCOUNT_TYPE = "codex"
DEFAULT_TOKENSOLO_MODELS = ["gpt-5.4"]


def normalize_tokensolo_models(models: Optional[Iterable[str] | str]) -> List[str]:
    if models is None:
        return list(DEFAULT_TOKENSOLO_MODELS)

    if isinstance(models, str):
        raw_items = models.replace("\n", ",").split(",")
    else:
        raw_items = list(models)

    normalized: List[str] = []
    seen = set()
    for item in raw_items:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        normalized.append(value)
        seen.add(value)
    return normalized or list(DEFAULT_TOKENSOLO_MODELS)


def build_tokensolo_import_url(api_url: str, channel: str = DEFAULT_TOKENSOLO_CHANNEL) -> str:
    raw = str(api_url or "").strip()
    if not raw:
        return ""

    normalized_channel = str(channel or DEFAULT_TOKENSOLO_CHANNEL).strip() or DEFAULT_TOKENSOLO_CHANNEL
    base = raw.rstrip("/")
    if base.endswith("/import"):
        return base
    if "/api/channel/" in base:
        return f"{base}/import"
    return f"{base}/api/channel/{normalized_channel}/import"


def _build_headers(import_secret: str) -> dict:
    return {
        "Content-Type": "application/json",
        "X-Codex-Import-Secret": str(import_secret or "").strip(),
    }


def upload_to_tokensolo(
    accounts: Sequence[Account],
    api_url: str,
    import_secret: str,
    channel: str = DEFAULT_TOKENSOLO_CHANNEL,
    account_type: str = DEFAULT_TOKENSOLO_ACCOUNT_TYPE,
    models: Optional[Iterable[str] | str] = None,
) -> Tuple[bool, str]:
    if not accounts:
        return False, "无可上传的账号"
    if not api_url:
        return False, "TokenSolo API URL 未配置"
    if not import_secret:
        return False, "TokenSolo Import Secret 未配置"

    normalized_models = normalize_tokensolo_models(models)
    payload_items = []
    for account in accounts:
        if not account.access_token:
            continue
        payload_items.append(
            {
                "access_token": account.access_token,
                "account_id": account.account_id or "",
                "email": account.email or "",
                "type": str(account_type or DEFAULT_TOKENSOLO_ACCOUNT_TYPE).strip() or DEFAULT_TOKENSOLO_ACCOUNT_TYPE,
                "models": normalized_models,
            }
        )

    if not payload_items:
        return False, "所有账号均缺少 access_token，无法上传"

    url = build_tokensolo_import_url(api_url, channel=channel)
    headers = _build_headers(import_secret)
    payload = {"payload": payload_items}

    try:
        response = cffi_requests.post(
            url,
            headers=headers,
            json=payload,
            proxies=None,
            timeout=30,
            impersonate="chrome110",
        )
        if response.status_code in (200, 201):
            return True, f"成功上传 {len(payload_items)} 个账号到 TokenSolo"
        if response.status_code == 401:
            return False, "连接成功，但 Import Secret 无效"
        if response.status_code == 403:
            return False, "连接成功，但无权导入到该 TokenSolo 渠道"
        error_message = f"上传失败: HTTP {response.status_code}"
        try:
            detail = response.json()
            if isinstance(detail, dict):
                error_message = detail.get("message") or detail.get("detail") or detail.get("error") or error_message
        except Exception:
            if response.text:
                error_message = f"{error_message} - {response.text[:200]}"
        return False, error_message
    except Exception as exc:
        logger.error("TokenSolo 上传异常: %s", exc)
        return False, f"上传异常: {exc}"


def batch_upload_to_tokensolo(
    account_ids: List[int],
    api_url: str,
    import_secret: str,
    channel: str = DEFAULT_TOKENSOLO_CHANNEL,
    account_type: str = DEFAULT_TOKENSOLO_ACCOUNT_TYPE,
    models: Optional[Iterable[str] | str] = None,
) -> dict:
    results = {
        "success_count": 0,
        "failed_count": 0,
        "skipped_count": 0,
        "details": [],
    }

    with get_db() as db:
        accounts: List[Account] = []
        for account_id in account_ids:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                results["failed_count"] += 1
                results["details"].append({"id": account_id, "email": None, "success": False, "error": "账号不存在"})
                continue
            if not account.access_token:
                results["skipped_count"] += 1
                results["details"].append({"id": account.id, "email": account.email, "success": False, "error": "缺少 access_token"})
                continue
            accounts.append(account)

        if not accounts:
            return results

        success, message = upload_to_tokensolo(
            accounts,
            api_url=api_url,
            import_secret=import_secret,
            channel=channel,
            account_type=account_type,
            models=models,
        )
        bucket = "success_count" if success else "failed_count"
        detail_key = "message" if success else "error"
        for account in accounts:
            results[bucket] += 1
            results["details"].append(
                {"id": account.id, "email": account.email, "success": success, detail_key: message}
            )
        return results


def test_tokensolo_connection(
    api_url: str,
    import_secret: str,
    channel: str = DEFAULT_TOKENSOLO_CHANNEL,
) -> Tuple[bool, str]:
    if not api_url:
        return False, "API URL 不能为空"
    if not import_secret:
        return False, "Import Secret 不能为空"

    url = build_tokensolo_import_url(api_url, channel=channel)
    headers = _build_headers(import_secret)

    try:
        response = cffi_requests.post(
            url,
            headers=headers,
            json={"payload": []},
            proxies=None,
            timeout=10,
            impersonate="chrome110",
        )
        if response.status_code in (200, 201, 204):
            return True, "TokenSolo 连接测试成功"
        if response.status_code == 400:
            return True, "TokenSolo 连接测试成功"
        if response.status_code == 401:
            return False, "连接成功，但 Import Secret 无效"
        if response.status_code == 403:
            return False, "连接成功，但当前 Secret 无权访问该渠道"
        if response.status_code == 404:
            return False, "TokenSolo 导入地址不存在，请检查 API URL 或 channel"
        return False, f"服务器返回异常状态码: {response.status_code}"
    except cffi_requests.exceptions.ConnectionError as exc:
        return False, f"无法连接到服务器: {exc}"
    except cffi_requests.exceptions.Timeout:
        return False, "连接超时，请检查网络配置"
    except Exception as exc:
        return False, f"连接测试失败: {exc}"
