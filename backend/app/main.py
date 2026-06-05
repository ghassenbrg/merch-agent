from contextlib import asynccontextmanager
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import config, drafts, runs, workflows
from app.core.logging import configure_logging
from app.db.database import init_database, seed_database
from app.services.config_service import validate_config_contracts
from app.services.scheduler_service import scheduler_loop


logger = logging.getLogger("merch_agent.startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    validate_config_contracts()
    init_database()
    seed_database()
    logger.info("Merch Agent API started", extra={"event": "startup", "phase": "phase10"})
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(drafts.router, prefix="/api/drafts", tags=["drafts"])
app.include_router(runs.router, prefix="/api/runs", tags=["runs"])
app.include_router(config.router, prefix="/api", tags=["config"])
app.include_router(workflows.router, prefix="/api", tags=["workflows"])
