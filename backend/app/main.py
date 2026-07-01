from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.admin import router as admin_router
from app.api.v1.admin_catalogue import router as admin_catalogue_router
from app.api.v1.allergies import router as allergies_router
from app.api.v1.auth import router as auth_router
from app.api.v1.conditions import router as conditions_router
from app.api.v1.export import router as export_router
from app.api.v1.family_history import router as family_history_router
from app.api.v1.files import router as files_router
from app.api.v1.health import router as health_router
from app.api.v1.immunizations import router as immunizations_router
from app.api.v1.lab import router as lab_router
from app.api.v1.medications import router as medications_router
from app.api.v1.observations import router as observations_router
from app.api.v1.patients import router as patients_router
from app.api.v1.preferences import router as preferences_router
from app.api.v1.summary import router as summary_router
from app.core.config import settings

app = FastAPI(title=settings.app_name, docs_url="/docs", openapi_url="/openapi.json")

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(patients_router, prefix="/api/v1")
app.include_router(conditions_router, prefix="/api/v1")
app.include_router(allergies_router, prefix="/api/v1")
app.include_router(medications_router, prefix="/api/v1")
app.include_router(immunizations_router, prefix="/api/v1")
app.include_router(family_history_router, prefix="/api/v1")
app.include_router(observations_router, prefix="/api/v1")
app.include_router(files_router, prefix="/api/v1")
app.include_router(lab_router, prefix="/api/v1")
app.include_router(summary_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")
app.include_router(preferences_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(admin_catalogue_router, prefix="/api/v1")
