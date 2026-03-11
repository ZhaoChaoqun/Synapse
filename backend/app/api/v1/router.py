"""
API v1 Router - Aggregates all endpoint routers
"""

from fastapi import APIRouter

from app.api.v1.endpoints import agent, crawler, intelligence, platforms

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(agent.router)
api_router.include_router(crawler.router)
api_router.include_router(intelligence.router)
api_router.include_router(platforms.router)
