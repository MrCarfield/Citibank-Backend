"""
Forecast 模块的 Pydantic Schema 定义

根据最新版接口文档/Forecast定义
"""
from enum import Enum
from typing import List, Optional, Dict
from datetime import datetime, date
from pydantic import BaseModel, Field


# ==================== 枚举类型 ====================

class MarketType(str, Enum):
    """市场类型"""
    WTI = "WTI"
    BRENT = "Brent"


class HorizonType(str, Enum):
    """预测周期"""
    ONE_WEEK = "1w"
    ONE_MONTH = "1m"
    ONE_QUARTER = "1q"


class RiskLevel(str, Enum):
    """风险等级"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ConfidenceLevel(str, Enum):
    """置信度等级"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RiskDriverType(str, Enum):
    """风险驱动类型"""
    VOLATILITY = "VOLATILITY"
    EVENT = "EVENT"
    MACRO_COINCIDENCE = "MACRO_COINCIDENCE"
    LIQUIDITY = "LIQUIDITY"
    TERM_STRUCTURE = "TERM_STRUCTURE"
    OTHER = "OTHER"


class TriggerSeverity(str, Enum):
    """触发严重程度"""
    INFO = "INFO"
    WARN = "WARN"
    CRITICAL = "CRITICAL"


class DirectionType(str, Enum):
    """方向类型"""
    UP = "UP"
    DOWN = "DOWN"
    NEUTRAL = "NEUTRAL"


class FactorCategory(str, Enum):
    """因子类别"""
    SUPPLY = "SUPPLY"
    DEMAND = "DEMAND"
    MACRO_FINANCIAL = "MACRO_FINANCIAL"
    FX = "FX"
    EVENTS = "EVENTS"
    OTHER = "OTHER"


# ==================== 基础模型 ====================

class PricePoint(BaseModel):
    """价格点"""
    ts: datetime = Field(..., description="时间戳")
    value: float = Field(..., description="价格值")


class Probabilities(BaseModel):
    """方向概率分布"""
    up: float = Field(..., ge=0, le=1, description="上涨概率")
    flat: float = Field(..., ge=0, le=1, description="持平概率")
    down: float = Field(..., ge=0, le=1, description="下跌概率")


class RiskDriver(BaseModel):
    """风险驱动因素"""
    type: RiskDriverType = Field(..., description="驱动类型")
    weight: float = Field(..., ge=0, le=1, description="权重")
    note: Optional[str] = Field(None, description="说明 [需要LLM生成]")


class RiskTrigger(BaseModel):
    """风险触发条件"""
    if_condition: str = Field(..., alias="if", description="触发条件 [需要LLM生成]")
    then_action: str = Field(..., alias="then", description="后续影响 [需要LLM生成]")
    severity: TriggerSeverity = Field(..., description="严重程度")

    class Config:
        populate_by_name = True


class BacktestMetric(BaseModel):
    """回测指标"""
    name: str = Field(..., description="指标名称")
    value: float = Field(..., description="指标值")
    unit: Optional[str] = Field(None, description="单位")


class EvaluationWindow(BaseModel):
    """评估窗口"""
    start: date = Field(..., description="开始日期")
    end: date = Field(..., description="结束日期")
    isOutOfSample: bool = Field(..., description="是否为样本外数据")


class FactorContribution(BaseModel):
    """因子贡献"""
    factorId: str = Field(..., description="因子ID")
    factorName: str = Field(..., description="因子名称")
    category: FactorCategory = Field(..., description="因子类别")
    direction: DirectionType = Field(..., description="影响方向")
    strength: float = Field(..., ge=0, le=1, description="影响强度")
    evidence: List[str] = Field(default_factory=list, description="证据列表")


# ==================== 预测曲线数据模型（对应前端页面） ====================

class ForecastCurvePoint(BaseModel):
    """预测曲线数据点（匹配backend.md算法输出格式）"""
    day: int = Field(..., description="预测天数")
    forecast_price: float = Field(..., description="预测价格")


class FactorImportance(BaseModel):
    """因子组贡献度（匹配backend.md算法输出格式）"""
    technical: float = Field(..., description="技术因子贡献度")
    macro: float = Field(..., description="宏观因子贡献度")
    supply: float = Field(..., description="供需因子贡献度")
    events: float = Field(..., description="事件因子贡献度")


class RiskProbs(BaseModel):
    """风险等级概率分布（匹配backend.md算法输出格式）"""
    low: float = Field(..., description="低风险概率")
    medium: float = Field(..., description="中风险概率")
    high: float = Field(..., description="高风险概率")


class RiskSignalItem(BaseModel):
    """风险信号项（对应前端风险信号分析）"""
    name: str = Field(..., description="风险名称")
    description: str = Field(..., description="风险描述")
    level: RiskLevel = Field(..., description="风险等级")


class TransmissionPathNode(BaseModel):
    """风险传导路径节点"""
    label: str = Field(..., description="节点标签")
    description: Optional[str] = Field(None, description="节点描述")


class DrivingFactor(BaseModel):
    """驱动因子"""
    factor: str = Field(..., description="因子名称")
    impactRate: float = Field(..., description="影响概率 (%)")
    description: str = Field(..., description="描述 [需要LLM生成]")


class StressTestScenario(BaseModel):
    """情景压力测试场景"""
    scenario: str = Field(..., description="场景名称")
    oilPriceChange: str = Field(..., description="油价变动描述")
    industryImpact: Dict[str, str] = Field(..., description="行业影响 {行业: 变动百分比}")


# ==================== API 响应模型 ====================

class ForecastDistributionResponse(BaseModel):
    """
    GET /v1/forecast/distribution 响应
    获取概率预测分布
    """
    horizon: HorizonType = Field(..., description="预测周期")
    asOf: datetime = Field(..., description="数据时间点")
    market: MarketType = Field(..., description="市场类型")
    median: float = Field(..., description="中位数预测价格")
    p10: float = Field(..., description="10%分位数价格")
    p90: float = Field(..., description="90%分位数价格")
    probabilities: Probabilities = Field(..., description="方向概率分布")
    modelId: str = Field(..., description="模型ID")
    modelVersion: str = Field(..., description="模型版本")

    class Config:
        json_schema_extra = {
            "example": {
                "horizon": "1w",
                "asOf": "2026-02-13T10:00:00Z",
                "market": "WTI",
                "median": 74.7,
                "p10": 73.2,
                "p90": 76.0,
                "probabilities": {"up": 0.35, "flat": 0.40, "down": 0.25},
                "modelId": "oil-forecast-v3",
                "modelVersion": "3.2.1"
            }
        }


class RiskSignalResponse(BaseModel):
    """
    GET /v1/forecast/signal 响应
    获取风险信号
    """
    market: MarketType = Field(..., description="市场类型")
    asOf: datetime = Field(..., description="数据时间点")
    horizon: HorizonType = Field(..., description="预测周期")
    level: RiskLevel = Field(..., description="风险等级")
    drivers: List[RiskDriver] = Field(..., description="风险驱动因素")
    triggers: List[RiskTrigger] = Field(..., description="触发条件")

    class Config:
        json_schema_extra = {
            "example": {
                "market": "WTI",
                "asOf": "2026-02-13T10:00:00Z",
                "horizon": "1w",
                "level": "HIGH",
                "drivers": [
                    {"type": "VOLATILITY", "weight": 0.85, "note": "波动率快速抬升"},
                    {"type": "EVENT", "weight": 0.70, "note": "突发地缘政治事件"}
                ],
                "triggers": [
                    {"if": "油价单日波动超过3%", "then": "可能触发程序化交易止损", "severity": "WARN"}
                ]
            }
        }


class ModelConfidenceResponse(BaseModel):
    """
    GET /v1/forecast/confidence 响应
    获取模型置信度和失败场景
    """
    market: MarketType = Field(..., description="市场类型")
    asOf: datetime = Field(..., description="数据时间点")
    horizon: HorizonType = Field(..., description="预测周期")
    confidence: ConfidenceLevel = Field(..., description="置信度等级")
    reasons: List[str] = Field(..., description="置信度原因 [需要LLM生成]")
    failureScenarios: List[str] = Field(..., description="失败场景 [需要LLM生成]")

    class Config:
        json_schema_extra = {
            "example": {
                "market": "WTI",
                "asOf": "2026-02-13T10:00:00Z",
                "horizon": "1w",
                "confidence": "MEDIUM",
                "reasons": [
                    "历史相似regime下模型表现良好",
                    "当前市场结构与训练数据匹配度较高"
                ],
                "failureScenarios": [
                    "突发地缘政治事件导致供给中断",
                    "美联储政策意外转向"
                ]
            }
        }


class BacktestSummaryResponse(BaseModel):
    """
    GET /v1/forecast/backtest 响应
    获取回测摘要
    """
    market: MarketType = Field(..., description="市场类型")
    horizon: HorizonType = Field(..., description="预测周期")
    asOf: datetime = Field(..., description="数据时间点")
    evaluationWindow: EvaluationWindow = Field(..., description="评估窗口")
    modelMetrics: List[BacktestMetric] = Field(..., description="模型指标")
    baselineMetrics: List[BacktestMetric] = Field(..., description="基线指标")
    bestRegimes: List[str] = Field(default_factory=list, description="最佳表现的市场状态")
    notes: Optional[str] = Field(None, description="综合分析说明 [需要LLM生成]")

    class Config:
        json_schema_extra = {
            "example": {
                "market": "WTI",
                "horizon": "1w",
                "asOf": "2026-02-13T10:00:00Z",
                "evaluationWindow": {
                    "start": "2025-08-01",
                    "end": "2026-02-01",
                    "isOutOfSample": True
                },
                "modelMetrics": [
                    {"name": "MAE", "value": 1.23, "unit": "$/bbl"},
                    {"name": "Direction Accuracy", "value": 0.68, "unit": "%"}
                ],
                "baselineMetrics": [
                    {"name": "MAE", "value": 2.15, "unit": "$/bbl"},
                    {"name": "Direction Accuracy", "value": 0.52, "unit": "%"}
                ],
                "bestRegimes": ["SUPPLY_DRIVEN", "DEMAND_DRIVEN"],
                "notes": "模型在供给驱动和需求驱动的市场状态下表现最佳"
            }
        }


# ==================== 扩展响应模型（支持前端页面完整需求） ====================

class ForecastOverviewResponse(BaseModel):
    """
    GET /v1/forecast/overview 响应
    预测总览（匹配backend.md算法输出格式）
    """
    date: str = Field(..., description="预测生成日期")
    current_price: float = Field(..., description="当前WTI价格")
    forecast_price: float = Field(..., description="预测窗口末的价格")
    direction: str = Field(..., description="方向判断 (up/down)")
    direction_prob: float = Field(..., description="上涨概率 (0-1)")
    risk_level: str = Field(..., description="风险等级 (low/medium/high)")
    risk_probs: RiskProbs = Field(..., description="风险等级概率分布")
    factor_importance: FactorImportance = Field(..., description="因子组贡献度")
    forecast_horizon: int = Field(..., description="模型训练预测窗口（天）")
    forecast_curve: List[ForecastCurvePoint] = Field(..., description="未来1~N天的价格序列")
    summary: str = Field(..., description="预测总结 [需要LLM生成]")

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2026-02-09",
                "current_price": 64.53,
                "forecast_price": 62.93,
                "direction": "down",
                "direction_prob": 0.00057,
                "risk_level": "medium",
                "risk_probs": {
                    "low": 0.00007,
                    "medium": 0.99963,
                    "high": 0.00030
                },
                "factor_importance": {
                    "technical": 0.62,
                    "macro": 0.51,
                    "supply": 0.55,
                    "events": 0.47
                },
                "forecast_horizon": 10,
                "forecast_curve": [
                    {"day": 1, "forecast_price": 64.37},
                    {"day": 2, "forecast_price": 64.21},
                    {"day": 3, "forecast_price": 64.05},
                    {"day": 4, "forecast_price": 63.88},
                    {"day": 5, "forecast_price": 63.72},
                    {"day": 6, "forecast_price": 63.56},
                    {"day": 7, "forecast_price": 63.40},
                    {"day": 8, "forecast_price": 63.25},
                    {"day": 9, "forecast_price": 63.09},
                    {"day": 10, "forecast_price": 62.93}
                ],
                "summary": "近期供给侧扰动叠加库存回落，油价在高位震荡"
            }
        }


class RiskSignalAnalysisResponse(BaseModel):
    """
    GET /v1/forecast/risk-analysis 响应
    风险信号分析（对应前端页面1的风险信号分析模块）
    """
    market: MarketType = Field(..., description="市场类型")
    asOf: datetime = Field(..., description="数据时间点")
    signals: List[RiskSignalItem] = Field(..., description="风险信号列表")

    class Config:
        json_schema_extra = {
            "example": {
                "market": "WTI",
                "asOf": "2026-02-13T10:00:00Z",
                "signals": [
                    {"name": "价格波动风险", "description": "波动率快速抬升", "level": "HIGH"},
                    {"name": "事件风险", "description": "突发地缘政治", "level": "MEDIUM"},
                    {"name": "结构性风险", "description": "供需错配", "level": "LOW"},
                    {"name": "预测不确定性风险", "description": "模型分歧扩大", "level": "HIGH"}
                ]
            }
        }


class TransmissionPathResponse(BaseModel):
    """
    GET /v1/forecast/transmission-path 响应
    风险传导路径
    """
    market: MarketType = Field(..., description="市场类型")
    asOf: datetime = Field(..., description="数据时间点")
    nodes: List[TransmissionPathNode] = Field(..., description="传导路径节点")

    class Config:
        json_schema_extra = {
            "example": {
                "market": "WTI",
                "asOf": "2026-02-13T10:00:00Z",
                "nodes": [
                    {"label": "地缘冲突", "description": None},
                    {"label": "原油供应收紧", "description": None},
                    {"label": "油价上涨", "description": None},
                    {"label": "航空燃油成本上升", "description": None},
                    {"label": "航空企业利润承压", "description": None},
                    {"label": "银行信用风险上升", "description": None}
                ]
            }
        }


class DrivingFactorsResponse(BaseModel):
    """
    GET /v1/forecast/drivers 响应
    驱动因子
    """
    market: MarketType = Field(..., description="市场类型")
    asOf: datetime = Field(..., description="数据时间点")
    factors: List[DrivingFactor] = Field(..., description="驱动因子列表")

    class Config:
        json_schema_extra = {
            "example": {
                "market": "WTI",
                "asOf": "2026-02-13T10:00:00Z",
                "factors": [
                    {"factor": "供给侧与需求侧", "impactRate": 85, "description": "OPEC+减产预期增强"},
                    {"factor": "库存与实物平衡", "impactRate": 70, "description": "全球原油库存回落"},
                    {"factor": "美元与利率", "impactRate": 60, "description": "利率预期放缓"},
                    {"factor": "地缘政治与事件影响", "impactRate": 90, "description": "中东局势升温"},
                    {"factor": "市场结构与期货", "impactRate": 20, "description": "价差结构稳定"},
                    {"factor": "波动率与情绪", "impactRate": 75, "description": "隐含波动率上行"}
                ]
            }
        }


class StressTestResponse(BaseModel):
    """
    GET /v1/forecast/stress-test 响应
    情景压力测试
    """
    market: MarketType = Field(..., description="市场类型")
    asOf: datetime = Field(..., description="数据时间点")
    scenarios: List[StressTestScenario] = Field(..., description="压力测试场景")

    class Config:
        json_schema_extra = {
            "example": {
                "market": "WTI",
                "asOf": "2026-02-13T10:00:00Z",
                "scenarios": [
                    {
                        "scenario": "OPEC+取消减产",
                        "oilPriceChange": "油价变动 -10.5 $/bbl",
                        "industryImpact": {"上游开采": "-25%", "炼化加工": "+15%", "航运物流": "+8%"}
                    },
                    {
                        "scenario": "红海航线完全恢复",
                        "oilPriceChange": "油价变动 -3.2 $/bbl",
                        "industryImpact": {"上游开采": "-6%", "炼化加工": "+5%", "航运物流": "-12%"}
                    }
                ]
            }
        }
