"""
全局定时任务调度器 (APScheduler)
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.triggers.cron import CronTrigger
import logging

logger = logging.getLogger(__name__)

# 使用单例模式或全局变量存储调度器实例
scheduler = AsyncIOScheduler(
    jobstores={"default": MemoryJobStore()},
    timezone="Asia/Shanghai",  # 明确时区
)


def register_jobs():
    """注册所有定时任务"""
    from app.tasks.generate_forecast_cache import daily_forecast_cache_job
    
    # 每天0:00执行Forecast缓存生成任务
    scheduler.add_job(
        daily_forecast_cache_job,
        trigger=CronTrigger(hour=0, minute=0),
        id="daily_forecast_cache",
        name="每日Forecast缓存生成",
        replace_existing=True,
        misfire_grace_time=3600  # 允许1小时的容错时间
    )
    logger.info("✅ 已注册定时任务: daily_forecast_cache (每天 00:00)")


def start_scheduler():
    """启动调度器"""
    try:
        if not scheduler.running:
            # 先注册任务
            register_jobs()
            # 启动调度器
            scheduler.start()
            logger.info("✅ 定时任务调度器已启动")
    except Exception as e:
        logger.error(f"❌ 调度器启动失败: {e}")

def shutdown_scheduler():
    """关闭调度器"""
    try:
        if scheduler.running:
            scheduler.shutdown()
            logger.info("👋 定时任务调度器已关闭")
    except Exception as e:
        logger.error(f"❌ 调度器关闭失败: {e}")
