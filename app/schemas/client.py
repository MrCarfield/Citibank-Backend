"""
Client Pydantic Schema
"""
from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field


class ClientType(str, Enum):
    UPSTREAM = "UPSTREAM"
    TRADER = "TRADER"
    DOWNSTREAM = "DOWNSTREAM"


class ExposureDirection(str, Enum):
    BENEFITS_FROM_UP = "BENEFITS_FROM_UP"
    HURT_BY_UP = "HURT_BY_UP"
    MIXED = "MIXED"


class PassThroughAbility(str, Enum):
    STRONG = "STRONG"
    MEDIUM = "MEDIUM"
    WEAK = "WEAK"


class FinancialBuffer(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class VolatilitySensitivity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ClientProfileBase(BaseModel):
    """客户档案基础Schema"""
    name: str = Field(..., description="客户名称")
    type: ClientType = Field(..., description="客户类型")
    currency: Optional[str] = Field(default="USD", description="货币")
    exposure_direction: ExposureDirection = Field(..., description="敞口方向")
    pass_through_ability: PassThroughAbility = Field(..., description="价格传导能力")
    financial_buffer: FinancialBuffer = Field(..., description="财务缓冲")
    volatility_sensitivity: VolatilitySensitivity = Field(..., description="波动率敏感度")
    notes: Optional[str] = Field(default=None, description="备注")


class ClientProfileCreate(ClientProfileBase):
    """创建客户档案请求Schema"""
    pass


class ClientProfile(ClientProfileBase):
    """客户档案响应Schema"""
    client_id: str = Field(..., description="客户ID")
    created_at: Optional[datetime] = Field(default=None, description="创建时间")
    updated_at: Optional[datetime] = Field(default=None, description="更新时间")
    
    class Config:
        from_attributes = True


class ClientListQuery(BaseModel):
    """客户列表查询参数"""
    q: Optional[str] = Field(default=None, description="按名称搜索")
    type: Optional[ClientType] = Field(default=None, description="按类型筛选")
    limit: Optional[int] = Field(default=100, description="返回数量限制")
