"""FastAPI app — Georgia Foreclosure API."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import analytics, auctions, counties, health, ingestion, notices, properties, sources
from .config import get_settings
from .schemas import ErrorResponse

settings = get_settings()

app = FastAPI(title="Georgia Foreclosure API", version="0.1.0", description="Data-first foreclosure ingestion + analytics. No mock data in production.")


# CORS: Next.js origin only — never "*"
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": str(exc), "code": "internal_error"})


app.include_router(health.router)
app.include_router(counties.router)
app.include_router(properties.router)
app.include_router(notices.router)
app.include_router(auctions.router)
app.include_router(analytics.router)
app.include_router(ingestion.router)
app.include_router(sources.router)


@app.get("/", include_in_schema=False)
def root():
    return {"service": "Georgia Foreclosure API", "docs": "/docs", "health": "/health"}
