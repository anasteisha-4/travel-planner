from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.exceptions import AppException
from app.routers import budget, itinerary, models_info, recommendations, validation

app = FastAPI(
    title="Travel Planner ML Service",
    description="ML recommendations, budget prediction, and trip validation",
    version="0.1.0",
)

cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+|10\.\d+\.\d+\.\d+)(:\d+)?",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

app.include_router(recommendations.router, prefix="/api/v1", tags=["Recommendations"])
app.include_router(budget.router, prefix="/api/v1", tags=["Budget"])
app.include_router(validation.router, prefix="/api/v1", tags=["Validation"])
app.include_router(itinerary.router, prefix="/api/v1", tags=["Itinerary"])
app.include_router(models_info.router, prefix="/api/v1", tags=["Models"])


@app.exception_handler(AppException)
async def app_exception_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.code, "message": exc.message})


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ml-service",
    }
