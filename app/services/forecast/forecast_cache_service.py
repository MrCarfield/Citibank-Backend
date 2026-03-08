"""
Forecast 缓存服务 - 处理多AI生成数据的存储和读取
"""
from datetime import date, datetime
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert
from app.db.session import async_session
from app.models.market import ForecastCache, MarketType


class ForecastCacheService:
    """Forecast缓存服务"""
    
    @staticmethod
    async def get_latest_cache(
        market: MarketType,
        target_date: Optional[date] = None
    ) -> Optional[ForecastCache]:
        """
        获取指定市场最新的缓存数据
        
        Args:
            market: 市场类型 (WTI/Brent)
            target_date: 目标日期，不传则获取最新日期的缓存
            
        Returns:
            ForecastCache对象或None
        """
        async with async_session() as session:
            if target_date:
                # 获取指定日期的缓存
                query = select(ForecastCache).where(
                    ForecastCache.market == market,
                    ForecastCache.cache_date == target_date
                )
            else:
                # 获取最新日期的缓存
                query = select(ForecastCache).where(
                    ForecastCache.market == market
                ).order_by(ForecastCache.cache_date.desc()).limit(1)
            
            result = await session.execute(query)
            return result.scalar_one_or_none()
    
    @staticmethod
    async def save_cache(
        market: MarketType,
        cache_date: date,
        cache_name: str,
        algorithm_data: Dict[str, Any],
        api_data: Dict[str, Any]
    ) -> ForecastCache:
        """
        保存Forecast缓存数据
        
        Args:
            market: 市场类型
            cache_date: 缓存日期
            cache_name: 缓存名称 (如: "2026-03-06算法预测")
            algorithm_data: 算法模型原始输出数据
            api_data: 包含所有API端点数据的字典
            
        Returns:
            保存的ForecastCache对象
        """
        async with async_session() as session:
            # 使用 upsert (INSERT ... ON DUPLICATE KEY UPDATE)
            stmt = insert(ForecastCache).values(
                market=market,
                cache_date=cache_date,
                cache_name=cache_name,
                algorithm_data=algorithm_data,
                distribution_data=api_data.get('distribution', {}),
                signal_data=api_data.get('signal', {}),
                confidence_data=api_data.get('confidence', {}),
                backtest_data=api_data.get('backtest', {}),
                overview_data=api_data.get('overview', {}),
                risk_analysis_data=api_data.get('risk_analysis', {}),
                transmission_path_data=api_data.get('transmission_path', {}),
                drivers_data=api_data.get('drivers', {}),
                stress_test_data=api_data.get('stress_test', {}),
                created_at=datetime.utcnow()
            )
            
            # 如果已存在则更新
            update_stmt = stmt.on_duplicate_key_update(
                cache_name=stmt.inserted.cache_name,
                algorithm_data=stmt.inserted.algorithm_data,
                distribution_data=stmt.inserted.distribution_data,
                signal_data=stmt.inserted.signal_data,
                confidence_data=stmt.inserted.confidence_data,
                backtest_data=stmt.inserted.backtest_data,
                overview_data=stmt.inserted.overview_data,
                risk_analysis_data=stmt.inserted.risk_analysis_data,
                transmission_path_data=stmt.inserted.transmission_path_data,
                drivers_data=stmt.inserted.drivers_data,
                stress_test_data=stmt.inserted.stress_test_data,
                created_at=stmt.inserted.created_at
            )
            
            await session.execute(update_stmt)
            await session.commit()
            
            # 返回保存的记录
            query = select(ForecastCache).where(
                ForecastCache.market == market,
                ForecastCache.cache_date == cache_date
            )
            result = await session.execute(query)
            return result.scalar_one()
    
    @staticmethod
    async def get_cache_by_name(
        market: MarketType,
        cache_name: str
    ) -> Optional[ForecastCache]:
        """
        根据缓存名称获取缓存数据
        
        Args:
            market: 市场类型
            cache_name: 缓存名称
            
        Returns:
            ForecastCache对象或None
        """
        async with async_session() as session:
            query = select(ForecastCache).where(
                ForecastCache.market == market,
                ForecastCache.cache_name == cache_name
            )
            result = await session.execute(query)
            return result.scalar_one_or_none()
    
    @staticmethod
    async def delete_old_caches(
        market: MarketType,
        keep_days: int = 30
    ) -> int:
        """
        删除指定市场过期的缓存数据
        
        Args:
            market: 市场类型
            keep_days: 保留最近多少天的数据
            
        Returns:
            删除的记录数
        """
        from sqlalchemy import delete
        from datetime import timedelta
        
        cutoff_date = date.today() - timedelta(days=keep_days)
        
        async with async_session() as session:
            stmt = delete(ForecastCache).where(
                ForecastCache.market == market,
                ForecastCache.cache_date < cutoff_date
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount


# 全局服务实例
forecast_cache_service = ForecastCacheService()
