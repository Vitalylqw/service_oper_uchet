"""
Main FastAPI application.

Provides REST API for data synchronization system with authentication,
RBAC authorization, and comprehensive endpoints for deals, sync sessions, and audit.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .auth.router import auth_router
from .config import config
from .endpoints.deals import deals_router
from .endpoints.health import health_router
from .endpoints.sessions import sessions_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events for the FastAPI application.
    """
        # Startup
    logger.info(f"Starting FastAPI application in {config.environment} mode")

    # TODO: Initialize database connections, repositories, etc.
    # This will be implemented when we integrate with infrastructure layer
    # For now using mock services through dependency injection

    yield

    # Shutdown
    logger.info("Shutting down FastAPI application")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        FastAPI: Configured application instance
    """
    app = FastAPI(
        title="Service Oper Uchet API",
        description="REST API for Excel to PostgreSQL data synchronization system",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router, prefix="/health", tags=["Health"])
    app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
    app.include_router(deals_router, prefix="/api/v1/deals", tags=["Deals"])
    app.include_router(sessions_router, prefix="/api/v1/sessions", tags=["Sync Sessions"])

    # Add root endpoint
    @app.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint with API information."""
        return {
            "name": "Service Oper Uchet API",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health"
        }

    return app


# Create application instance
app = create_app()
