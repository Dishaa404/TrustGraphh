from fastapi import APIRouter

from app.config import get_settings
from app.tigergraph import graph_client

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
            "tigergraph": graph_client.service_status(),
            "registry": "configured" if settings.registry_configured else "unconfigured",
            "payments": "configured" if settings.cake_wallet_configured else "unconfigured",
            "payment_provider": settings.payment_provider,
        },
    }
