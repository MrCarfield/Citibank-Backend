"""
Client 服务层 - 客户档案管理
"""
import uuid
from typing import Optional, List
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.schemas.client import ClientProfile, ClientProfileCreate, ClientType


class ClientService:
    """客户档案服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def list_clients(
        self,
        q: Optional[str] = None,
        type: Optional[ClientType] = None,
        limit: int = 100
    ) -> List[ClientProfile]:
        """获取客户列表"""
        query = select(Client)
        
        # 构建过滤条件
        filters = []
        if q:
            # 使用不区分大小写的搜索
            from sqlalchemy import func
            filters.append(func.lower(Client.name).contains(func.lower(q)))
        if type:
            filters.append(Client.type == type.value)
        
        if filters:
            query = query.where(and_(*filters))
        
        query = query.limit(limit)
        result = await self.db.execute(query)
        clients = result.scalars().all()
        
        return [ClientProfile.model_validate(client) for client in clients]
    
    async def get_client(self, client_id: str) -> Optional[ClientProfile]:
        """根据ID获取客户档案"""
        query = select(Client).where(Client.client_id == client_id)
        result = await self.db.execute(query)
        client = result.scalar_one_or_none()
        
        if client:
            return ClientProfile.model_validate(client)
        return None
    
    async def create_client(self, data: ClientProfileCreate) -> ClientProfile:
        """创建客户档案"""
        client = Client(
            client_id=str(uuid.uuid4()),
            name=data.name,
            type=data.type.value,
            currency=data.currency or "USD",
            exposure_direction=data.exposure_direction.value,
            pass_through_ability=data.pass_through_ability.value,
            financial_buffer=data.financial_buffer.value,
            volatility_sensitivity=data.volatility_sensitivity.value,
            notes=data.notes
        )
        
        self.db.add(client)
        await self.db.commit()
        await self.db.refresh(client)
        
        return ClientProfile.model_validate(client)
    
    async def update_client(
        self,
        client_id: str,
        data: ClientProfileCreate
    ) -> Optional[ClientProfile]:
        """更新客户档案"""
        query = select(Client).where(Client.client_id == client_id)
        result = await self.db.execute(query)
        client = result.scalar_one_or_none()
        
        if not client:
            return None
        
        # 更新字段
        client.name = data.name
        client.type = data.type.value
        client.currency = data.currency or "USD"
        client.exposure_direction = data.exposure_direction.value
        client.pass_through_ability = data.pass_through_ability.value
        client.financial_buffer = data.financial_buffer.value
        client.volatility_sensitivity = data.volatility_sensitivity.value
        client.notes = data.notes
        
        await self.db.commit()
        await self.db.refresh(client)
        
        return ClientProfile.model_validate(client)
    
    async def delete_client(self, client_id: str) -> bool:
        """删除客户档案"""
        query = select(Client).where(Client.client_id == client_id)
        result = await self.db.execute(query)
        client = result.scalar_one_or_none()
        
        if not client:
            return False
        
        await self.db.delete(client)
        await self.db.commit()
        
        return True


# 便捷函数
async def get_client_service(db: AsyncSession) -> ClientService:
    """获取Client服务实例"""
    return ClientService(db)
