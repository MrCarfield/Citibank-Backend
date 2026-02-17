"""
Client 数据模型
"""
from sqlalchemy import Column, String, Enum, DateTime, func
from sqlalchemy.dialects.mysql import ENUM
from app.db.base import Base


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


class Client(Base):
    """客户档案模型"""
    __tablename__ = "clients"
    
    client_id = Column(String(64), primary_key=True, comment="客户ID")
    name = Column(String(255), nullable=False, comment="客户名称")
    type = Column(ENUM("UPSTREAM", "TRADER", "DOWNSTREAM"), nullable=False, comment="客户类型")
    currency = Column(String(10), default="USD", comment="货币")
    exposure_direction = Column(
        ENUM("BENEFITS_FROM_UP", "HURT_BY_UP", "MIXED"),
        nullable=False,
        comment="敞口方向"
    )
    pass_through_ability = Column(
        ENUM("STRONG", "MEDIUM", "WEAK"),
        nullable=False,
        comment="价格传导能力"
    )
    financial_buffer = Column(
        ENUM("HIGH", "MEDIUM", "LOW"),
        nullable=False,
        comment="财务缓冲"
    )
    volatility_sensitivity = Column(
        ENUM("HIGH", "MEDIUM", "LOW"),
        nullable=False,
        comment="波动率敏感度"
    )
    notes = Column(String(1000), nullable=True, comment="备注")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
