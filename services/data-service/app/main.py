import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.observability import add_observability
from app.observability import store as observability_store
from app.routers import destinations, internal

app = FastAPI(title="Triply Data Service", version="1.0.0", docs_url="/docs")
add_observability(app, "data-service")

ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

app.include_router(destinations.router, prefix="/api")
app.include_router(internal.router, prefix="/internal")


@app.get("/health")
def health():
    return {"status": "ok", "service": "data-service"}


@app.get("/internal/observability/metrics")
def observability_metrics():
    return observability_store.snapshot()
