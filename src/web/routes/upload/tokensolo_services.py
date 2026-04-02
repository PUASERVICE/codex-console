"""
TokenSolo 服务管理 API 路由
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ....core.upload.tokensolo_upload import (
    batch_upload_to_tokensolo,
    normalize_tokensolo_models,
    test_tokensolo_connection,
)
from ....database import crud
from ....database.session import get_db

router = APIRouter()


class TokenSoloServiceCreate(BaseModel):
    name: str
    api_url: str = "https://tokensolo.com/api/channel/codex/import"
    import_secret: str
    channel: str = "codex"
    account_type: str = "codex"
    models: str = "gpt-5.4"
    enabled: bool = True
    priority: int = 0


class TokenSoloServiceUpdate(BaseModel):
    name: Optional[str] = None
    api_url: Optional[str] = None
    import_secret: Optional[str] = None
    channel: Optional[str] = None
    account_type: Optional[str] = None
    models: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None


class TokenSoloServiceResponse(BaseModel):
    id: int
    name: str
    api_url: str
    channel: str
    account_type: str
    models: List[str]
    has_secret: bool
    enabled: bool
    priority: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class TokenSoloTestRequest(BaseModel):
    api_url: Optional[str] = None
    import_secret: Optional[str] = None
    channel: str = "codex"


class TokenSoloUploadRequest(BaseModel):
    account_ids: List[int]
    service_id: Optional[int] = None


def _to_response(service) -> TokenSoloServiceResponse:
    return TokenSoloServiceResponse(
        id=service.id,
        name=service.name,
        api_url=service.api_url,
        channel=service.channel or "codex",
        account_type=service.account_type or "codex",
        models=normalize_tokensolo_models(service.models),
        has_secret=bool(service.import_secret),
        enabled=service.enabled,
        priority=service.priority,
        created_at=service.created_at.isoformat() if service.created_at else None,
        updated_at=service.updated_at.isoformat() if service.updated_at else None,
    )


@router.get("", response_model=List[TokenSoloServiceResponse])
async def list_tokensolo_services(enabled: Optional[bool] = None):
    with get_db() as db:
        services = crud.get_tokensolo_services(db, enabled=enabled)
        return [_to_response(service) for service in services]


@router.post("", response_model=TokenSoloServiceResponse)
async def create_tokensolo_service(request: TokenSoloServiceCreate):
    with get_db() as db:
        service = crud.create_tokensolo_service(
            db,
            name=request.name,
            api_url=request.api_url,
            import_secret=request.import_secret,
            channel=request.channel,
            account_type=request.account_type,
            models=",".join(normalize_tokensolo_models(request.models)),
            enabled=request.enabled,
            priority=request.priority,
        )
        return _to_response(service)


@router.get("/{service_id}", response_model=TokenSoloServiceResponse)
async def get_tokensolo_service(service_id: int):
    with get_db() as db:
        service = crud.get_tokensolo_service_by_id(db, service_id)
        if not service:
            raise HTTPException(status_code=404, detail="TokenSolo 服务不存在")
        return _to_response(service)


@router.patch("/{service_id}", response_model=TokenSoloServiceResponse)
async def update_tokensolo_service(service_id: int, request: TokenSoloServiceUpdate):
    with get_db() as db:
        service = crud.get_tokensolo_service_by_id(db, service_id)
        if not service:
            raise HTTPException(status_code=404, detail="TokenSolo 服务不存在")

        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.api_url is not None:
            update_data["api_url"] = request.api_url
        if request.import_secret:
            update_data["import_secret"] = request.import_secret
        if request.channel is not None:
            update_data["channel"] = request.channel
        if request.account_type is not None:
            update_data["account_type"] = request.account_type
        if request.models is not None:
            update_data["models"] = ",".join(normalize_tokensolo_models(request.models))
        if request.enabled is not None:
            update_data["enabled"] = request.enabled
        if request.priority is not None:
            update_data["priority"] = request.priority

        updated = crud.update_tokensolo_service(db, service_id, **update_data)
        return _to_response(updated)


@router.delete("/{service_id}")
async def delete_tokensolo_service(service_id: int):
    with get_db() as db:
        service = crud.get_tokensolo_service_by_id(db, service_id)
        if not service:
            raise HTTPException(status_code=404, detail="TokenSolo 服务不存在")
        crud.delete_tokensolo_service(db, service_id)
        return {"success": True, "message": f"TokenSolo 服务 {service.name} 已删除"}


@router.post("/{service_id}/test")
async def test_tokensolo_service(service_id: int):
    with get_db() as db:
        service = crud.get_tokensolo_service_by_id(db, service_id)
        if not service:
            raise HTTPException(status_code=404, detail="TokenSolo 服务不存在")
        success, message = test_tokensolo_connection(
            service.api_url,
            service.import_secret,
            channel=service.channel or "codex",
        )
        return {"success": success, "message": message}


@router.post("/test-connection")
async def test_tokensolo_connection_direct(request: TokenSoloTestRequest):
    if not request.api_url or not request.import_secret:
        raise HTTPException(status_code=400, detail="api_url 和 import_secret 不能为空")
    success, message = test_tokensolo_connection(
        request.api_url,
        request.import_secret,
        channel=request.channel or "codex",
    )
    return {"success": success, "message": message}


@router.post("/upload")
async def upload_accounts_to_tokensolo(request: TokenSoloUploadRequest):
    if not request.account_ids:
        raise HTTPException(status_code=400, detail="账号 ID 列表不能为空")

    with get_db() as db:
        if request.service_id:
            service = crud.get_tokensolo_service_by_id(db, request.service_id)
        else:
            services = crud.get_tokensolo_services(db, enabled=True)
            service = services[0] if services else None

        if not service:
            raise HTTPException(status_code=400, detail="未找到可用的 TokenSolo 服务")

        api_url = service.api_url
        import_secret = service.import_secret
        channel = service.channel or "codex"
        account_type = service.account_type or "codex"
        models = service.models or "gpt-5.4"

    return batch_upload_to_tokensolo(
        request.account_ids,
        api_url=api_url,
        import_secret=import_secret,
        channel=channel,
        account_type=account_type,
        models=models,
    )
