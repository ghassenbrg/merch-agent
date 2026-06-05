from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import drafts, workflows
from app.db.database import init_database, seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    seed_database()
    yield


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
app.include_router(workflows.router, prefix="/api", tags=["workflows"])
