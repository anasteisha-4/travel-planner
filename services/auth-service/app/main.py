"""
Auth Service
Handles user authentication, registration, and profile management
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, users
from app.database import engine, Base

app = FastAPI(
    title="Travel Planner Auth Service",
    description="Authentication and user management service",
    version="0.1.0",
)

Base.metadata.create_all(bind=engine)
cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])


@app.get("/health")
async def health_check():
    from app import redis_client
    redis_ok = redis_client.check_redis_connection()
    return {
        "status": "healthy" if redis_ok else "degraded",
        "service": "auth-service",
        "redis": "connected" if redis_ok else "disconnected"
    }
