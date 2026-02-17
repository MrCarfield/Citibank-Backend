from enum import Enum
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

# --- Enums ---

class Market(str, Enum):
    WTI = "WTI"
    Brent = "Brent"

class Horizon(str, Enum):
    ONE_WEEK = "1w"
    ONE_MONTH = "1m"
    ONE_QUARTER = "1q"

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

class StressLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class DriverCategory(str, Enum):
    SUPPLY = "SUPPLY"
    DEMAND = "DEMAND"
    MACRO_FINANCIAL = "MACRO_FINANCIAL"
    FX = "FX"
    EVENTS = "EVENTS"
    OTHER = "OTHER"

class Direction(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    NEUTRAL = "NEUTRAL"
    MIXED = "MIXED"
    UNCERTAIN = "UNCERTAIN"

# --- Request Models ---

class ScenarioOverride(BaseModel):
    priceShockPct: Optional[float] = None
    volatilityShockPct: Optional[float] = None
    eventTag: Optional[str] = None

class TranslatorRequest(BaseModel):
    clientId: str
    market: Market
    horizon: Horizon
    asOf: Optional[datetime] = None
    scenario: Optional[ScenarioOverride] = None

# --- Response Models ---

class ClientProfile(BaseModel):
    clientId: str
    name: str
    type: ClientType
    currency: str = "USD"
    exposureDirection: ExposureDirection
    passThroughAbility: PassThroughAbility
    financialBuffer: FinancialBuffer
    volatilitySensitivity: VolatilitySensitivity
    notes: Optional[str] = None

class ImpactScore(BaseModel):
    operatingStress: StressLevel
    fundingStress: StressLevel
    confidence: float = Field(..., ge=0, le=1)

class FactorContribution(BaseModel):
    factorId: str
    factorName: str
    category: DriverCategory
    direction: Direction
    strength: float = Field(..., ge=0, le=1)
    evidence: Optional[List[str]] = None

class TransmissionStep(BaseModel):
    from_node: str = Field(..., alias="from")
    to_node: str = Field(..., alias="to")
    note: Optional[str] = None
    direction: Direction

class TranslatorResponse(BaseModel):
    client: ClientProfile
    market: Market
    horizon: Horizon
    asOf: Optional[datetime] = None
    assumptions: Optional[List[str]] = None
    impactScore: ImpactScore
    keyDrivers: List[FactorContribution]
    transmissionPath: List[TransmissionStep]
    rmTalkPoints: List[str]
    bankActionChecklist: List[str]
