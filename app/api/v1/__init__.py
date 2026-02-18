"""
API v1 版本路由
"""
from fastapi import APIRouter
from app.api.v1.endpoints import health, forecast, client, auth, translator, market

api_router = APIRouter()

# 注册路由
api_router.include_router(health.router, tags=["健康检查"])
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(translator.router, prefix="/translator", tags=["Translator"])
api_router.include_router(market.router, prefix="/market", tags=["Market"])
api_router.include_router(forecast.router, prefix="/forecast", tags=["Forecast"])
api_router.include_router(client.router, prefix="/clients", tags=["Clients"])
