"""
API v1 版本路由
"""
from fastapi import APIRouter
from app.api.v1.endpoints import health, forecast, client

api_router = APIRouter()

# 注册路由
api_router.include_router(health.router, tags=["健康检查"])
api_router.include_router(forecast.router, prefix="/forecast", tags=["Forecast"])
api_router.include_router(client.router, prefix="/clients", tags=["Clients"])
