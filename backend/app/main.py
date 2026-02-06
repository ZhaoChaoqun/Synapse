"""
FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    print(f"🚀 Starting InsightSentinel Backend v{app.version}")
    print(f"📡 Environment: {settings.environment}")

    # TODO: Initialize database connection pool
    # TODO: Initialize Redis connection
    # TODO: Initialize Gemini client

    yield

    # Shutdown
    print("👋 Shutting down InsightSentinel Backend")
    # TODO: Close database connections
    # TODO: Close Redis connections


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="InsightSentinel API",
        description="7x24 AI Intelligence Agent for GCR Market",
        version="0.1.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API router
    app.include_router(api_router)

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        from app.core.llm.router import check_llm_availability

        llm_status = await check_llm_availability()

        return {
            "status": "healthy",
            "version": app.version,
            "environment": settings.environment,
            "llm": llm_status,
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
    )
