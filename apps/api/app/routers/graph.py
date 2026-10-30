from fastapi import APIRouter

from app.tigergraph import graph_client

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/rings")
def sybil_rings(min_mutual: int = 2, min_devices: int = 2) -> dict:
    return graph_client.sybil_rings(min_mutual=min_mutual, min_devices=min_devices)


@router.get("/explain/{did}")
def explain(did: str) -> dict:
    return graph_client.explain_trust(did)
