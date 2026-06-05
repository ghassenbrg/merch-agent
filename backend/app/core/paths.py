from pathlib import Path
import os


REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.environ.get("MERCH_AGENT_DATA_DIR", REPO_ROOT / "data"))
CONFIG_DIR = REPO_ROOT / "config"
DATABASE_PATH = DATA_DIR / "merch_agent.sqlite3"


def ensure_data_directories() -> None:
    for path in [
        DATA_DIR,
        DATA_DIR / "drafts",
        DATA_DIR / "designs",
        DATA_DIR / "research_snapshots",
        DATA_DIR / "screenshots",
        DATA_DIR / "logs",
    ]:
        path.mkdir(parents=True, exist_ok=True)
