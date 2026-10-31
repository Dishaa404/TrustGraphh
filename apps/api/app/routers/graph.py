from fastapi import APIRouter, HTTPException

from app.tigergraph import graph_client

router = APIRouter(prefix="/graph", tags=["graph"])


def require_graph() -> None:
    if not graph_client.configured:
        raise HTTPException(status_code=503, detail="TigerGraph is not configured")


@router.get("/rings")
def sybil_rings(min_mutual: int = 2, min_devices: int = 2) -> dict:
    require_graph()
    return graph_client.sybil_rings(min_mutual=min_mutual, min_devices=min_devices)


@router.get("/explain/{did}")
def explain(did: str) -> dict:
    require_graph()
    return graph_client.explain_trust(did)
