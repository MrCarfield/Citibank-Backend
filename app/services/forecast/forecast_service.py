"""
Forecast 服务实现 - 从缓存读取多AI生成的数据

数据来源:
1. 数据库中的 ForecastCache 表（由定时任务生成）
2. 如果缓存不存在，降级使用 Mock 数据

缓存生成流程:
- 每天0点定时任务读取 backend.md 算法数据
- 使用多AI模型(LLM Council)生成所有API数据
- 保存到数据库，命名格式: YYYY-MM-DD算法预测
"""
from datetime import datetime, date, timedelta
from typing import Optional, List
import asyncio
from app.schemas.forecast import (
    MarketType,
    HorizonType,
    RiskLevel,
    ConfidenceLevel,
    RiskDriverType,
    TriggerSeverity,
    FactorCategory,
    DirectionType,
    Probabilities,
    RiskDriver,
    RiskTrigger,
    BacktestMetric,
    EvaluationWindow,
    ForecastCurvePoint,
    FactorImportance,
    RiskProbs,
    RiskSignalItem,
    TransmissionPathNode,
    DrivingFactor,
    StressTestScenario,
    ForecastDistributionResponse,
    RiskSignalResponse,
    ModelConfidenceResponse,
    BacktestSummaryResponse,
    ForecastOverviewResponse,
    RiskSignalAnalysisResponse,
    TransmissionPathResponse,
    DrivingFactorsResponse,
    StressTestResponse,
)
from app.services.forecast.forecast_cache_service import forecast_cache_service


# ==================== 配置 ====================

# 是否启用LLM生成（设为False时使用Mock数据）
ENABLE_LLM = True


# ==================== Mock 数据常量（匹配backend.md算法输出格式） ====================

# 基础预测数据（对应backend.md格式）
MOCK_DATE = "2026-02-09"
MOCK_CURRENT_PRICE = 64.53
MOCK_FORECAST_PRICE = 62.928237034454945
MOCK_DIRECTION = "down"
MOCK_DIRECTION_PROB = 0.0005699765752069652
MOCK_RISK_LEVEL = "medium"
MOCK_FORECAST_HORIZON = 10

# 风险概率分布（对应backend.md risk_probs）
MOCK_RISK_PROBS = {
    "low": 6.998850585659966e-05,
    "medium": 0.9996311664581299,
    "high": 0.0002988271589856595
}

# 因子贡献度（对应backend.md factor_importance）
MOCK_FACTOR_IMPORTANCE = {
    "technical": 0.6201432943344116,
    "macro": 0.5081236362457275,
    "supply": 0.5529541969299316,
    "events": 0.4713454246520996
}

# 预测曲线（对应backend.md forecast_curve格式）
MOCK_FORECAST_CURVE = [
    {"day": 1, "forecast_price": 64.36800590830231},
    {"day": 2, "forecast_price": 64.2064184815007},
    {"day": 3, "forecast_price": 64.04523669871638},
    {"day": 4, "forecast_price": 63.884459541633284},
    {"day": 5, "forecast_price": 63.72408599449172},
    {"day": 6, "forecast_price": 63.56411504408194},
    {"day": 7, "forecast_price": 63.404545679737694},
    {"day": 8, "forecast_price": 63.24537689332992},
    {"day": 9, "forecast_price": 63.08660767926028},
    {"day": 10, "forecast_price": 62.92823703445492},
]

# Mock fallback文本
MOCK_DRIVER_NOTES = {
    RiskDriverType.VOLATILITY: "波动率快速抬升，20日历史波动率突破25%阈值",
    RiskDriverType.EVENT: "中东地缘紧张局势升级，红海航运受阻",
    RiskDriverType.MACRO_COINCIDENCE: "美联储政策信号与欧央行预期分化",
    RiskDriverType.TERM_STRUCTURE: "期限结构呈现backwardation，近月升水扩大",
    RiskDriverType.LIQUIDITY: "市场流动性收紧，买卖价差扩大",
    RiskDriverType.OTHER: "其他风险因素需持续关注",
}

MOCK_REASONS = [
    "当前市场处于supply-driven regime，与训练数据分布匹配度较高",
    "近30日模型方向预测准确率达68%，处于历史中位水平",
    "主要驱动因子(OPEC+政策、库存)的信号强度在模型敏感区间内",
    "期限结构状态稳定，减少了套利行为对预测的干扰",
]

MOCK_FAILURE_SCENARIOS = [
    "突发地缘政治事件导致供给中断，历史训练数据难以覆盖",
    "美联储政策意外转向，引发美元剧烈波动和资金流重新配置",
    "中国经济刺激政策超预期，需求端出现结构性变化",
    "OPEC+内部分歧加剧导致减产协议瓦解",
    "气候异常事件影响炼厂运营和运输物流",
]

MOCK_BACKTEST_NOTES = (
    "在6个月样本外测试期内，模型相对naive随机游走基准显著优于基线，"
    "MAE降低43%，方向准确率提升16个百分点。模型在供给驱动和需求驱动的市场"
    "状态下表现最佳，但在事件驱动的高波动期表现有所下降。"
)

MOCK_FORECAST_SUMMARY = (
    "近期供给侧扰动叠加库存回落，油价在高位震荡；"
    "模型区间显示短期上行空间收窄，但地缘事件仍可能触发快速波动。"
)

MOCK_FACTOR_DESCRIPTIONS = {
    "供给侧与需求侧": "OPEC+减产预期增强，新兴市场需求复苏提供支撑。",
    "库存与实物平衡": "全球原油库存回落，现货溢价抬升短期风险。",
    "美元与利率": "利率预期放缓，美元走弱放大风险敏感度。",
    "地缘政治与事件影响": "中东局势升温，引发供应中断担忧。",
    "市场结构与期货": "价差结构稳定，对当前风险影响有限。",
    "波动率与情绪": "隐含波动率上行，情绪推动短线放大。",
}


# ==================== LLM辅助函数 ====================

# ==================== API实现 ====================

async def get_forecast_distribution(
    market: MarketType,
    horizon: HorizonType,
    as_of: Optional[datetime] = None
) -> ForecastDistributionResponse:
    """获取概率预测分布 - 从缓存读取"""
    now = as_of or datetime.utcnow()
    
    # 尝试从缓存读取
    cache = await forecast_cache_service.get_latest_cache(market)
    if cache and cache.distribution_data:
        data = cache.distribution_data
        return ForecastDistributionResponse(
            horizon=HorizonType(data.get('horizon', horizon.value)),
            asOf=now,
            market=MarketType(data.get('market', market.value)),
            median=data.get('median', 74.7),
            p10=data.get('p10', 73.2),
            p90=data.get('p90', 76.0),
            probabilities=Probabilities(**data.get('probabilities', {"up": 0.35, "flat": 0.40, "down": 0.25})),
            modelId=data.get('modelId', 'oil-forecast-ensemble-v3'),
            modelVersion=data.get('modelVersion', '3.2.1')
        )
    
    # 缓存不存在时使用默认值
    horizon_multiplier = {"1w": 1.0, "1m": 1.5, "1q": 2.0}
    mult = horizon_multiplier.get(horizon.value, 1.0)
    base_price = 74.7 if market == MarketType.WTI else 78.95
    
    return ForecastDistributionResponse(
        horizon=horizon,
        asOf=now,
        market=market,
        median=round(base_price, 2),
        p10=round(base_price - 1.5 * mult, 2),
        p90=round(base_price + 1.3 * mult, 2),
        probabilities=Probabilities(up=0.35, flat=0.40, down=0.25),
        modelId="oil-forecast-ensemble-v3",
        modelVersion="3.2.1"
    )


async def get_risk_signal(
    market: MarketType,
    horizon: HorizonType,
    as_of: Optional[datetime] = None
) -> RiskSignalResponse:
    """获取风险信号 - 从缓存读取"""
    now = as_of or datetime.utcnow()
    
    # 尝试从缓存读取
    cache = await forecast_cache_service.get_latest_cache(market)
    if cache and cache.signal_data:
        data = cache.signal_data
        drivers_raw = data.get('drivers', [])
        drivers = [
            RiskDriver(
                type=RiskDriverType(d.get('type', 'OTHER')),
                weight=d.get('weight', 0.5),
                note=d.get('note', '风险因素需关注')
            )
            for d in drivers_raw
        ]
        triggers_raw = data.get('triggers', [])
        triggers = [
            RiskTrigger(
                if_condition=t.get('if', ''),
                then_action=t.get('then', ''),
                severity=TriggerSeverity(t.get('severity', 'INFO'))
            )
            for t in triggers_raw
        ]
        return RiskSignalResponse(
            market=market,
            asOf=now,
            horizon=horizon,
            level=RiskLevel(data.get('level', 'MEDIUM')),
            drivers=drivers,
            triggers=triggers
        )
    
    # 缓存不存在时使用Mock数据
    drivers_data = [
        (RiskDriverType.VOLATILITY, 0.85),
        (RiskDriverType.EVENT, 0.70),
        (RiskDriverType.MACRO_COINCIDENCE, 0.55),
        (RiskDriverType.TERM_STRUCTURE, 0.40),
    ]
    drivers = [RiskDriver(type=dt, weight=w, note=MOCK_DRIVER_NOTES.get(dt, "风险因素需关注")) for dt, w in drivers_data]
    
    triggers = [
        RiskTrigger(if_condition="OPEC+成员国出现产量执行分歧", then_action="可能导致减产协议松动，供给预期上修", severity=TriggerSeverity.WARN),
        RiskTrigger(if_condition="EIA周度库存降幅超预期超过500万桶", then_action="短期供需偏紧信号强化，支撑油价", severity=TriggerSeverity.INFO),
        RiskTrigger(if_condition="美元指数突破105关口", then_action="压制大宗商品定价，油价承压", severity=TriggerSeverity.WARN),
        RiskTrigger(if_condition="中东冲突扩大至产油区", then_action="供给中断风险骤升，油价可能跳涨10%+", severity=TriggerSeverity.CRITICAL),
    ]
    
    return RiskSignalResponse(
        market=market, asOf=now, horizon=horizon,
        level=RiskLevel.MEDIUM, drivers=drivers, triggers=triggers
    )


async def get_model_confidence(
    market: MarketType,
    horizon: HorizonType,
    as_of: Optional[datetime] = None
) -> ModelConfidenceResponse:
    """获取模型置信度 - 从缓存读取"""
    now = as_of or datetime.utcnow()
    
    # 尝试从缓存读取
    cache = await forecast_cache_service.get_latest_cache(market)
    if cache and cache.confidence_data:
        data = cache.confidence_data
        return ModelConfidenceResponse(
            market=market,
            asOf=now,
            horizon=horizon,
            confidence=ConfidenceLevel(data.get('confidence', 'MEDIUM')),
            reasons=data.get('reasons', MOCK_REASONS),
            failureScenarios=data.get('failureScenarios', MOCK_FAILURE_SCENARIOS)
        )
    
    # 缓存不存在时使用Mock数据
    return ModelConfidenceResponse(
        market=market, asOf=now, horizon=horizon,
        confidence=ConfidenceLevel.MEDIUM, reasons=MOCK_REASONS, failureScenarios=MOCK_FAILURE_SCENARIOS
    )


async def get_backtest_summary(
    market: MarketType,
    horizon: HorizonType,
    start: date,
    end: date,
    out_of_sample: bool = True,
    as_of: Optional[datetime] = None
) -> BacktestSummaryResponse:
    """获取回测摘要 - 从缓存读取"""
    now = as_of or datetime.utcnow()
    
    # 尝试从缓存读取
    cache = await forecast_cache_service.get_latest_cache(market)
    if cache and cache.backtest_data:
        data = cache.backtest_data
        metrics_raw = data.get('modelMetrics', [])
        baseline_raw = data.get('baselineMetrics', [])
        return BacktestSummaryResponse(
            market=market,
            horizon=horizon,
            asOf=now,
            evaluationWindow=EvaluationWindow(
                start=start,
                end=end,
                isOutOfSample=out_of_sample
            ),
            modelMetrics=[BacktestMetric(**m) for m in metrics_raw],
            baselineMetrics=[BacktestMetric(**m) for m in baseline_raw],
            bestRegimes=data.get('bestRegimes', ["SUPPLY_DRIVEN", "DEMAND_DRIVEN"]),
            notes=data.get('notes', MOCK_BACKTEST_NOTES)
        )
    
    # 缓存不存在时使用Mock数据
    model_mae = 1.23
    baseline_mae = 2.15
    direction_accuracy = 0.68
    best_regimes = ["SUPPLY_DRIVEN", "DEMAND_DRIVEN"]
    
    return BacktestSummaryResponse(
        market=market,
        horizon=horizon,
        asOf=now,
        evaluationWindow=EvaluationWindow(
            start=start,
            end=end,
            isOutOfSample=out_of_sample
        ),
        modelMetrics=[
            BacktestMetric(name="MAE", value=model_mae, unit="$/bbl"),
            BacktestMetric(name="RMSE", value=1.67, unit="$/bbl"),
            BacktestMetric(name="Direction Accuracy", value=direction_accuracy, unit=None),
            BacktestMetric(name="Calibration Score", value=0.85, unit=None),
            BacktestMetric(name="Sharpe (signal-based)", value=1.42, unit=None),
        ],
        baselineMetrics=[
            BacktestMetric(name="MAE", value=baseline_mae, unit="$/bbl"),
            BacktestMetric(name="RMSE", value=2.89, unit="$/bbl"),
            BacktestMetric(name="Direction Accuracy", value=0.52, unit=None),
            BacktestMetric(name="Calibration Score", value=0.61, unit=None),
            BacktestMetric(name="Sharpe (signal-based)", value=0.73, unit=None),
        ],
        bestRegimes=best_regimes,
        notes=MOCK_BACKTEST_NOTES
    )


async def get_forecast_overview(
    market: MarketType,
    as_of: Optional[datetime] = None
) -> ForecastOverviewResponse:
    """获取预测总览 - 从缓存读取"""
    
    # 尝试从缓存读取
    cache = await forecast_cache_service.get_latest_cache(market)
    if cache and cache.overview_data:
        data = cache.overview_data
        forecast_curve = [ForecastCurvePoint(**point) for point in data.get('forecast_curve', MOCK_FORECAST_CURVE)]
        factor_importance = FactorImportance(**data.get('factor_importance', MOCK_FACTOR_IMPORTANCE))
        risk_probs = RiskProbs(**data.get('risk_probs', MOCK_RISK_PROBS))
        return ForecastOverviewResponse(
            date=data.get('date', MOCK_DATE),
            current_price=data.get('current_price', MOCK_CURRENT_PRICE),
            forecast_price=data.get('forecast_price', MOCK_FORECAST_PRICE),
            direction=data.get('direction', MOCK_DIRECTION),
            direction_prob=data.get('direction_prob', MOCK_DIRECTION_PROB),
            risk_level=data.get('risk_level', MOCK_RISK_LEVEL),
            risk_probs=risk_probs,
            factor_importance=factor_importance,
            forecast_horizon=data.get('forecast_horizon', MOCK_FORECAST_HORIZON),
            forecast_curve=forecast_curve,
            summary=data.get('summary', MOCK_FORECAST_SUMMARY)
        )
    
    # 缓存不存在时使用Mock数据
    forecast_curve = [ForecastCurvePoint(**point) for point in MOCK_FORECAST_CURVE]
    factor_importance = FactorImportance(**MOCK_FACTOR_IMPORTANCE)
    risk_probs = RiskProbs(**MOCK_RISK_PROBS)
    
    return ForecastOverviewResponse(
        date=MOCK_DATE,
        current_price=MOCK_CURRENT_PRICE,
        forecast_price=MOCK_FORECAST_PRICE,
        direction=MOCK_DIRECTION,
        direction_prob=MOCK_DIRECTION_PROB,
        risk_level=MOCK_RISK_LEVEL,
        risk_probs=risk_probs,
        factor_importance=factor_importance,
        forecast_horizon=MOCK_FORECAST_HORIZON,
        forecast_curve=forecast_curve,
        summary=MOCK_FORECAST_SUMMARY
    )


async def get_risk_analysis(
    market: MarketType,
    as_of: Optional[datetime] = None
) -> RiskSignalAnalysisResponse:
    """获取风险信号分析 - 从缓存读取"""
    now = as_of or datetime.utcnow()
    
    # 尝试从缓存读取
    cache = await forecast_cache_service.get_latest_cache(market)
    if cache and cache.risk_analysis_data:
        data = cache.risk_analysis_data
        signals_raw = data.get('signals', [])
        signals = [
            RiskSignalItem(
                name=s.get('name', ''),
                description=s.get('description', ''),
                level=RiskLevel(s.get('level', 'MEDIUM'))
            )
            for s in signals_raw
        ]
        return RiskSignalAnalysisResponse(
            market=market,
            asOf=now,
            signals=signals
        )
    
    # 缓存不存在时使用Mock数据
    return RiskSignalAnalysisResponse(
        market=market,
        asOf=now,
        signals=[
            RiskSignalItem(name="价格波动风险", description="波动率快速抬升", level=RiskLevel.HIGH),
            RiskSignalItem(name="事件风险", description="突发地缘政治", level=RiskLevel.MEDIUM),
            RiskSignalItem(name="结构性风险", description="供需错配", level=RiskLevel.LOW),
            RiskSignalItem(name="预测不确定性风险", description="模型分歧扩大", level=RiskLevel.HIGH),
        ]
    )


async def get_transmission_path(
    market: MarketType,
    as_of: Optional[datetime] = None
) -> TransmissionPathResponse:
    """获取风险传导路径 - 从缓存读取"""
    now = as_of or datetime.utcnow()
    
    # 尝试从缓存读取
    cache = await forecast_cache_service.get_latest_cache(market)
    if cache and cache.transmission_path_data:
        data = cache.transmission_path_data
        nodes_raw = data.get('nodes', [])
        nodes = [
            TransmissionPathNode(label=n.get('label', ''), description=n.get('description', ''))
            for n in nodes_raw
        ]
        return TransmissionPathResponse(
            market=market,
            asOf=now,
            nodes=nodes
        )
    
    # 缓存不存在时使用Mock数据
    nodes_data = [
        ("地缘冲突", "中东局势紧张"),
        ("原油供应收紧", "OPEC+减产执行"),
        ("油价上涨", "供需失衡推高"),
        ("航空燃油成本上升", "燃油成本增加"),
        ("航空企业利润承压", "航司利润下滑"),
        ("银行信用风险上升", "信贷风险暴露"),
    ]
    nodes = [TransmissionPathNode(label=label, description=desc) for label, desc in nodes_data]
    
    return TransmissionPathResponse(
        market=market,
        asOf=now,
        nodes=nodes
    )


async def get_driving_factors(
    market: MarketType,
    as_of: Optional[datetime] = None
) -> DrivingFactorsResponse:
    """获取驱动因子 - 从缓存读取"""
    now = as_of or datetime.utcnow()
    
    # 尝试从缓存读取
    cache = await forecast_cache_service.get_latest_cache(market)
    if cache and cache.drivers_data:
        data = cache.drivers_data
        factors_raw = data.get('factors', [])
        factors = [
            DrivingFactor(
                factor=f.get('factor', ''),
                impactRate=f.get('impactRate', 50),
                description=f.get('description', '')
            )
            for f in factors_raw
        ]
        return DrivingFactorsResponse(
            market=market,
            asOf=now,
            factors=factors
        )
    
    # 缓存不存在时使用Mock数据
    factors_data = [
        ("供给侧与需求侧", 85),
        ("库存与实物平衡", 70),
        ("美元与利率", 60),
        ("地缘政治与事件影响", 90),
        ("市场结构与期货", 20),
        ("波动率与情绪", 75),
    ]
    factors = [DrivingFactor(factor=fn, impactRate=ir, description=MOCK_FACTOR_DESCRIPTIONS.get(fn, f"{fn}对油价有影响。")) for fn, ir in factors_data]
    
    return DrivingFactorsResponse(
        market=market, asOf=now, factors=factors
    )


async def get_stress_test(
    market: MarketType,
    as_of: Optional[datetime] = None
) -> StressTestResponse:
    """获取情景压力测试 - 从缓存读取"""
    now = as_of or datetime.utcnow()
    
    # 尝试从缓存读取
    cache = await forecast_cache_service.get_latest_cache(market)
    if cache and cache.stress_test_data:
        data = cache.stress_test_data
        scenarios_raw = data.get('scenarios', [])
        scenarios = [
            StressTestScenario(
                scenario=s.get('scenario', ''),
                oilPriceChange=s.get('oilPriceChange', ''),
                industryImpact=s.get('industryImpact', {})
            )
            for s in scenarios_raw
        ]
        return StressTestResponse(
            market=market,
            asOf=now,
            scenarios=scenarios
        )
    
    # 缓存不存在时使用Mock数据
    return StressTestResponse(
        market=market,
        asOf=now,
        scenarios=[
            StressTestScenario(
                scenario="OPEC+取消减产",
                oilPriceChange="油价变动 -10.5 $/bbl",
                industryImpact={"上游开采": "-25%", "炼化加工": "+15%", "航运物流": "+8%"}
            ),
            StressTestScenario(
                scenario="红海航线完全恢复",
                oilPriceChange="油价变动 -3.2 $/bbl",
                industryImpact={"上游开采": "-6%", "炼化加工": "+5%", "航运物流": "-12%"}
            ),
            StressTestScenario(
                scenario="欧佩克意外增产50万桶/日",
                oilPriceChange="油价变动 -7.4 $/bbl",
                industryImpact={"上游开采": "-18%", "炼化加工": "+12%", "航运物流": "-4%"}
            ),
        ]
    )
