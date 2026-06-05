from contextlib import asynccontextmanager
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api import agent, config, drafts, runs, workflows
from app.core.health import readiness_status
from app.core.logging import configure_logging
from app.core.security import AccessControlMiddleware, SecurityHeadersMiddleware
from app.core.settings import get_settings, validate_runtime_settings
from app.db.database import init_database, seed_database
from app.services.config_service import validate_config_contracts
from app.services.scheduler_service import scheduler_loop


logger = logging.getLogger("merch_agent.startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = validate_runtime_settings()
    validate_config_contracts()
    init_database()
    seed_database()
    logger.info(
        "Merch Agent API started",
        extra={
            "event": "startup",
            "phase": "phase11",
            "environment": settings.environment,
            "auth_required": settings.auth_required,
        },
    )
    scheduler_task = asyncio.create_task(scheduler_loop())
    try:
        yield
    finally:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Merch Agent API", version="0.1.0", lifespan=lifespan)
settings = get_settings()

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AccessControlMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["authorization", "content-type", "x-merch-agent-token"],
)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def ready() -> dict[str, object]:
    return readiness_status()


app.include_router(drafts.router, prefix="/api/drafts", tags=["drafts"])
app.include_router(runs.router, prefix="/api/runs", tags=["runs"])
app.include_router(config.router, prefix="/api", tags=["config"])
app.include_router(workflows.router, prefix="/api", tags=["workflows"])
app.include_router(agent.router, prefix="/api", tags=["agent"])
