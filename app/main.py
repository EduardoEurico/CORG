"""Corrup.ORG FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database.db import init_db
from app.routers import analysis, funds, organizations


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialise the database on startup."""
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(organizations.router)
app.include_router(funds.router)
app.include_router(analysis.router)


@app.get("/", tags=["Health"], summary="API health check")
def health_check() -> dict:
    """Return basic API metadata confirming the service is running."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "ok",
    }
