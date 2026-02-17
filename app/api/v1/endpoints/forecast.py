"""
Forecast 路由端点

实现最新版接口文档/Forecast部分的所有API:
- GET /v1/forecast/distribution - 获取概率预测分布
- GET /v1/forecast/signal - 获取风险信号
- GET /v1/forecast/confidence - 获取模型置信度
- GET /v1/forecast/backtest - 获取回测摘要

扩展接口（支持前端页面完整需求）:
- GET /v1/forecast/overview - 预测总览
- GET /v1/forecast/risk-analysis - 风险信号分析
- GET /v1/forecast/transmission-path - 风险传导路径
- GET /v1/forecast/drivers - 驱动因子
- GET /v1/forecast/stress-test - 情景压力测试
"""
from datetime import datetime, date, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.schemas.forecast import (
    MarketType,
    HorizonType,
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
from app.services.forecast import (
    get_forecast_distribution,
    get_risk_signal,
    get_model_confidence,
    get_backtest_summary,
    get_forecast_overview,
    get_risk_analysis,
    get_transmission_path,
    get_driving_factors,
    get_stress_test,
)

router = APIRouter()


# ==================== 核心 Forecast API（最新版接口文档） ====================

@router.get(
    "/distribution",
    response_model=ForecastDistributionResponse,
    summary="获取概率预测分布",
    description="Get probabilistic forecast distribution for the Forecast & Risk Signal page"
)
async def forecast_distribution(
    market: MarketType = Query(
        ...,
        description="Reference crude benchmark (WTI/Brent)"
    ),
    horizon: HorizonType = Query(
        ...,
        description="Forecast horizon (1w/1m/1q)"
    ),
    asOf: Optional[datetime] = Query(
        None,
        description="ISO-8601 timestamp for point-in-time queries. If omitted, server uses latest."
    ),
):
    """
    获取概率预测分布
    
    返回指定市场和预测周期的概率分布预测，包括:
    - 中位数预测价格 (median)
    - 10%分位数价格 (p10) 
    - 90%分位数价格 (p90)
    - 方向概率分布 (up/flat/down)
    """
    try:
        return await get_forecast_distribution(
            market=market,
            horizon=horizon,
            as_of=asOf
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取预测分布失败: {str(e)}"
        )


@router.get(
    "/signal",
    response_model=RiskSignalResponse,
    summary="获取风险信号",
    description="Get risk signal (LOW/MEDIUM/HIGH) with triggers"
)
async def forecast_signal(
    market: MarketType = Query(
        ...,
        description="Reference crude benchmark (WTI/Brent)"
    ),
    horizon: HorizonType = Query(
        ...,
        description="Forecast horizon (1w/1m/1q)"
    ),
    asOf: Optional[datetime] = Query(
        None,
        description="ISO-8601 timestamp for point-in-time queries. If omitted, server uses latest."
    ),
):
    """
    获取风险信号
    
    返回当前风险等级及其驱动因素:
    - 风险等级 (LOW/MEDIUM/HIGH)
    - 风险驱动因素列表及权重
    - 触发条件和后续影响
    
    注意: drivers[].note 和 triggers[].if/then 字段可配置为LLM生成
    """
    try:
        return await get_risk_signal(
            market=market,
            horizon=horizon,
            as_of=asOf
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取风险信号失败: {str(e)}"
        )


@router.get(
    "/confidence",
    response_model=ModelConfidenceResponse,
    summary="获取模型置信度",
    description="Get model confidence and failure scenarios"
)
async def forecast_confidence(
    market: MarketType = Query(
        ...,
        description="Reference crude benchmark (WTI/Brent)"
    ),
    horizon: HorizonType = Query(
        ...,
        description="Forecast horizon (1w/1m/1q)"
    ),
    asOf: Optional[datetime] = Query(
        None,
        description="ISO-8601 timestamp for point-in-time queries. If omitted, server uses latest."
    ),
):
    """
    获取模型置信度和失败场景
    
    返回:
    - 置信度等级 (HIGH/MEDIUM/LOW)
    - 置信度原因列表 [需要LLM生成]
    - 可能导致预测失败的场景 [需要LLM生成]
    """
    try:
        return await get_model_confidence(
            market=market,
            horizon=horizon,
            as_of=asOf
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取模型置信度失败: {str(e)}"
        )


@router.get(
    "/backtest",
    response_model=BacktestSummaryResponse,
    summary="获取回测摘要",
    description="Get backtest summary and baseline comparison"
)
async def forecast_backtest(
    market: MarketType = Query(
        ...,
        description="Reference crude benchmark (WTI/Brent)"
    ),
    horizon: HorizonType = Query(
        ...,
        description="Forecast horizon (1w/1m/1q)"
    ),
    start: Optional[date] = Query(
        None,
        description="Evaluation window start date (YYYY-MM-DD), default: 180 days ago"
    ),
    end: Optional[date] = Query(
        None,
        description="Evaluation window end date (YYYY-MM-DD), default: today"
    ),
    outOfSample: bool = Query(
        True,
        description="Whether metrics are computed on out-of-sample data"
    ),
):
    """
    获取回测摘要和基线比较
    
    返回:
    - 评估窗口信息
    - 模型指标 (MAE, RMSE, Direction Accuracy等)
    - 基线指标对比
    - 最佳表现的市场状态
    - 综合分析说明 [需要LLM生成]
    """
    try:
        # 设置默认值
        if start is None:
            start = date.today() - timedelta(days=180)
        if end is None:
            end = date.today()
        
        # 验证日期范围
        if start >= end:
            raise HTTPException(
                status_code=400,
                detail="开始日期必须早于结束日期"
            )
        
        return await get_backtest_summary(
            market=market,
            horizon=horizon,
            start=start,
            end=end,
            out_of_sample=outOfSample
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取回测摘要失败: {str(e)}"
        )


# ==================== 扩展 Forecast API（支持前端页面完整需求） ====================

@router.get(
    "/overview",
    response_model=ForecastOverviewResponse,
    summary="获取预测总览",
    description="Get forecast overview for the main dashboard"
)
async def forecast_overview(
    market: MarketType = Query(
        MarketType.WTI,
        description="Reference crude benchmark (WTI/Brent)"
    ),
    asOf: Optional[datetime] = Query(
        None,
        description="ISO-8601 timestamp for point-in-time queries"
    ),
):
    """
    获取预测总览
    
    对应前端页面1顶部的"预测总览"模块，包含:
    - 当前价格和预测价格
    - 方向判断和概率
    - 风险等级
    - 预测曲线数据 (用于图表)
    - 预测总结 [需要LLM生成]
    """
    try:
        return await get_forecast_overview(
            market=market,
            as_of=asOf
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取预测总览失败: {str(e)}"
        )


@router.get(
    "/risk-analysis",
    response_model=RiskSignalAnalysisResponse,
    summary="获取风险信号分析",
    description="Get risk signal analysis breakdown"
)
async def forecast_risk_analysis(
    market: MarketType = Query(
        MarketType.WTI,
        description="Reference crude benchmark (WTI/Brent)"
    ),
    asOf: Optional[datetime] = Query(
        None,
        description="ISO-8601 timestamp for point-in-time queries"
    ),
):
    """
    获取风险信号分析
    
    对应前端页面1的"风险信号分析"模块，包含:
    - 价格波动风险
    - 事件风险
    - 结构性风险
    - 预测不确定性风险
    """
    try:
        return await get_risk_analysis(
            market=market,
            as_of=asOf
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取风险信号分析失败: {str(e)}"
        )


@router.get(
    "/transmission-path",
    response_model=TransmissionPathResponse,
    summary="获取风险传导路径",
    description="Get risk transmission path"
)
async def forecast_transmission_path(
    market: MarketType = Query(
        MarketType.WTI,
        description="Reference crude benchmark (WTI/Brent)"
    ),
    asOf: Optional[datetime] = Query(
        None,
        description="ISO-8601 timestamp for point-in-time queries"
    ),
):
    """
    获取风险传导路径
    
    对应前端页面1的"风险传导路径"模块，
    展示从风险源头到最终影响的传导链条
    """
    try:
        return await get_transmission_path(
            market=market,
            as_of=asOf
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取风险传导路径失败: {str(e)}"
        )


@router.get(
    "/drivers",
    response_model=DrivingFactorsResponse,
    summary="获取驱动因子",
    description="Get driving factors analysis"
)
async def forecast_drivers(
    market: MarketType = Query(
        MarketType.WTI,
        description="Reference crude benchmark (WTI/Brent)"
    ),
    asOf: Optional[datetime] = Query(
        None,
        description="ISO-8601 timestamp for point-in-time queries"
    ),
):
    """
    获取驱动因子
    
    对应前端页面1的"驱动因子"模块，包含:
    - 供给侧与需求侧
    - 库存与实物平衡
    - 美元与利率
    - 地缘政治与事件影响
    - 市场结构与期货
    - 波动率与情绪
    
    注意: factors[].description 字段可配置为LLM生成
    """
    try:
        return await get_driving_factors(
            market=market,
            as_of=asOf
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取驱动因子失败: {str(e)}"
        )


@router.get(
    "/stress-test",
    response_model=StressTestResponse,
    summary="获取情景压力测试",
    description="Get stress test scenarios"
)
async def forecast_stress_test(
    market: MarketType = Query(
        MarketType.WTI,
        description="Reference crude benchmark (WTI/Brent)"
    ),
    asOf: Optional[datetime] = Query(
        None,
        description="ISO-8601 timestamp for point-in-time queries"
    ),
):
    """
    获取情景压力测试
    
    对应前端页面1的"情景压力测试"模块，
    展示不同场景下的油价变动和行业影响
    """
    try:
        return await get_stress_test(
            market=market,
            as_of=asOf
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取情景压力测试失败: {str(e)}"
        )
