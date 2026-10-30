from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.version,
        "environment": settings.app_env,
        "services": {
            "tigergraph": "configured" if settings.tigergraph_configured else "demo",
            "payments": settings.payment_provider,
        },
    }
