from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, chain, credentials, graph, health, payments, persons

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Graph-native proof-of-personhood and credential verification.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(chain.router)
app.include_router(persons.router)
app.include_router(graph.router)
app.include_router(credentials.router)
app.include_router(payments.router)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"service": settings.app_name, "version": settings.version, "docs": "/docs"}
