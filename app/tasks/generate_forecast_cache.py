"""
Forecast缓存生成定时任务

每天0点执行：
1. 读取 backend.md 中的算法预测数据
2. 使用多AI模型生成所有Forecast API数据
3. 将结果保存到数据库，命名为 "YYYY-MM-DD算法预测"
"""
import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Any, Optional

from app.models.market import MarketType
from app.schemas.forecast import HorizonType
from app.services.forecast.llm_council_forecast_service import llm_council_forecast_service
from app.services.forecast.forecast_cache_service import forecast_cache_service

logger = logging.getLogger(__name__)

# 算法数据文件路径
BACKEND_MD_PATH = Path("d:/Citibank-Backend/backend.md")


def parse_algorithm_data_from_md(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    从 backend.md 文件中解析算法预测数据
    
    Args:
        file_path: backend.md 文件路径
        
    Returns:
        算法数据字典或None
    """
    try:
        if not file_path.exists():
            logger.error(f"算法数据文件不存在: {file_path}")
            return None
        
        content = file_path.read_text(encoding='utf-8')
        
        # 提取JSON部分（文件开头到第一个空行或字段说明）
        json_end = content.find('字段说明：')
        if json_end == -1:
            json_end = len(content)
        
        json_content = content[:json_end].strip()
        
        # 解析JSON
        algorithm_data = json.loads(json_content)
        logger.info(f"成功解析算法数据，日期: {algorithm_data.get('date', 'unknown')}")
        return algorithm_data
        
    except json.JSONDecodeError as e:
        logger.error(f"解析算法数据JSON失败: {e}")
        return None
    except Exception as e:
        logger.error(f"读取算法数据文件失败: {e}")
        return None


async def generate_forecast_cache_for_market(
    market: MarketType,
    target_date: Optional[date] = None
) -> bool:
    """
    为指定市场生成Forecast缓存
    
    Args:
        market: 市场类型 (WTI/Brent)
        target_date: 目标日期，不传则使用今天
        
    Returns:
        是否成功
    """
    try:
        # 1. 解析算法数据
        algorithm_data = parse_algorithm_data_from_md(BACKEND_MD_PATH)
        if not algorithm_data:
            logger.error("无法获取算法数据，跳过缓存生成")
            return False
        
        # 2. 确定日期和缓存名称
        cache_date = target_date or date.today()
        cache_name = f"{cache_date.isoformat()}算法预测"
        
        logger.info(f"开始生成Forecast缓存: market={market.value}, date={cache_date}, name={cache_name}")
        
        # 3. 使用多AI模型生成所有API数据
        logger.info("调用LLM Council生成Forecast数据...")
        api_data = await llm_council_forecast_service.generate_all_forecast_data(
            market=market,
            horizon=HorizonType.ONE_WEEK,  # 默认使用1周周期
            algorithm_data=algorithm_data
        )
        
        # 4. 保存到数据库
        logger.info("保存缓存到数据库...")
        cache = await forecast_cache_service.save_cache(
            market=market,
            cache_date=cache_date,
            cache_name=cache_name,
            algorithm_data=algorithm_data,
            api_data=api_data
        )
        
        logger.info(f"✅ Forecast缓存生成成功: {cache}")
        return True
        
    except Exception as e:
        logger.error(f"❌ 生成Forecast缓存失败: {e}", exc_info=True)
        return False


async def generate_all_forecast_caches(target_date: Optional[date] = None) -> Dict[str, bool]:
    """
    为所有市场生成Forecast缓存
    
    Args:
        target_date: 目标日期，不传则使用今天
        
    Returns:
        各市场的生成结果字典
    """
    results = {}
    
    for market in [MarketType.WTI, MarketType.Brent]:
        logger.info(f"=" * 50)
        logger.info(f"开始为 {market.value} 市场生成缓存...")
        success = await generate_forecast_cache_for_market(market, target_date)
        results[market.value] = success
    
    logger.info(f"=" * 50)
    logger.info(f"缓存生成完成: {results}")
    return results


async def daily_forecast_cache_job():
    """
    每日Forecast缓存生成任务（定时任务入口）
    
    建议配置：每天 00:00 执行
    """
    logger.info("=" * 60)
    logger.info(f"🕐 开始执行每日Forecast缓存生成任务: {datetime.now()}")
    logger.info("=" * 60)
    
    results = await generate_all_forecast_caches()
    
    # 统计结果
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    logger.info("=" * 60)
    logger.info(f"📊 任务完成: {success_count}/{total_count} 个市场缓存生成成功")
    logger.info("=" * 60)
    
    return results


# 用于手动触发的同步包装函数
def run_daily_forecast_cache_job_sync():
    """同步方式运行每日缓存生成任务（用于手动触发）"""
    import asyncio
    return asyncio.run(daily_forecast_cache_job())


if __name__ == "__main__":
    # 本地测试运行
    import asyncio
    logging.basicConfig(level=logging.INFO)
    
    # 测试生成今天的缓存
    result = asyncio.run(daily_forecast_cache_job())
    print(f"测试结果: {result}")
