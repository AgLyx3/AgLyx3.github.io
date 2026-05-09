"""Aggregate API router."""

from fastapi import APIRouter

from .actions import router as actions_router
from .analytics import router as analytics_router
from .chat import router as chat_router
from .graph import router as graph_router
from .health import router as health_router
from .topic_ops import router as topic_ops_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(chat_router)
api_router.include_router(graph_router)
api_router.include_router(topic_ops_router)
api_router.include_router(actions_router)
api_router.include_router(analytics_router)
