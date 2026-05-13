from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.exceptions import AppException
from app.observability import add_observability
from app.observability import store as observability_store
from app.routers import events, feedback
from app.routers.features import internal_router
from app.routers.features import router as features_router

app = FastAPI(
    title="Travel Planner Analytics Service",
    description="Event tracking, user features, and behavioral analytics",
    version="0.1.0",
)

add_observability(app, "analytics-service")

cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+|10\.\d+\.\d+\.\d+)(:\d+)?",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.code, "message": exc.message})


app.include_router(events.router)
app.include_router(feedback.router)
app.include_router(features_router)
app.include_router(internal_router)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "analytics-service",
    }


@app.get("/internal/observability/metrics")
async def observability_metrics():
    return observability_store.snapshot()
