"""
Client 路由端点

实现最新版接口文档/Clients部分的所有API:
- GET /v1/clients - 获取客户列表
- POST /v1/clients - 创建客户档案
- GET /v1/clients/{clientId} - 获取客户详情
- PUT /v1/clients/{clientId} - 更新客户档案
- DELETE /v1/clients/{clientId} - 删除客户档案
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.client import (
    ClientProfile,
    ClientProfileCreate,
    ClientType
)
from app.services.client import ClientService

router = APIRouter()


async def get_client_service(db: AsyncSession = Depends(get_db)) -> ClientService:
    """获取Client服务实例"""
    return ClientService(db)


@router.get(
    "",
    response_model=List[ClientProfile],
    summary="获取客户列表",
    description="List client profiles for the Client Profile Builder"
)
async def list_clients(
    q: Optional[str] = Query(None, description="Search by name (contains)"),
    type: Optional[ClientType] = Query(None, description="Filter by client type"),
    limit: Optional[int] = Query(100, description="Limit"),
    service: ClientService = Depends(get_client_service)
):
    """
    获取客户档案列表
    
    支持按名称搜索和按类型筛选
    """
    clients = await service.list_clients(q=q, type=type, limit=limit)
    return clients


@router.post(
    "",
    response_model=ClientProfile,
    status_code=status.HTTP_201_CREATED,
    summary="创建客户档案",
    description="Create a client profile"
)
async def create_client(
    data: ClientProfileCreate,
    service: ClientService = Depends(get_client_service)
):
    """
    创建新客户档案
    """
    client = await service.create_client(data)
    return client


@router.get(
    "/{client_id}",
    response_model=ClientProfile,
    summary="获取客户详情",
    description="Get client profile by id"
)
async def get_client(
    client_id: str,
    service: ClientService = Depends(get_client_service)
):
    """
    根据ID获取客户档案详情
    """
    client = await service.get_client(client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"客户不存在: {client_id}"
        )
    return client


@router.put(
    "/{client_id}",
    response_model=ClientProfile,
    summary="更新客户档案",
    description="Update a client profile (replace)"
)
async def update_client(
    client_id: str,
    data: ClientProfileCreate,
    service: ClientService = Depends(get_client_service)
):
    """
    更新客户档案（全量替换）
    """
    client = await service.update_client(client_id, data)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"客户不存在: {client_id}"
        )
    return client


@router.delete(
    "/{client_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除客户档案",
    description="Delete a client profile"
)
async def delete_client(
    client_id: str,
    service: ClientService = Depends(get_client_service)
):
    """
    删除客户档案
    """
    success = await service.delete_client(client_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"客户不存在: {client_id}"
        )
    return None
