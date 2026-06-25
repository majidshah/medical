from fastapi import FastAPI

from app.api.v1.health import router as health_router
from app.core.config import settings

app = FastAPI(title=settings.app_name, docs_url="/docs", openapi_url="/openapi.json")

app.include_router(health_router, prefix="/api/v1")
