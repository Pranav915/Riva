"""
Routers package for RIVA API
"""
from .auth import router as auth_router, user_router
from .finance_routes import router as finance_router
from .calendar_routes import router as calendar_router
from .todo_routes import router as todo_router
from .gemini_live import router as gemini_live_router

__all__ = [
    "auth_router",
    "user_router",
    "finance_router",
    "calendar_router",
    "todo_router",
    "gemini_live_router",
]
