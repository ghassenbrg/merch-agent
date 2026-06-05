from pathlib import Path
import os


REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.environ.get("MERCH_AGENT_DATA_DIR", REPO_ROOT / "data"))
CONFIG_DIR = REPO_ROOT / "config"
DATABASE_PATH = DATA_DIR / "merch_agent.sqlite3"


def resolve_runtime_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path.resolve()
    if path.parts and path.parts[0] == "data":
        return (DATA_DIR / Path(*path.parts[1:])).resolve()
    return (REPO_ROOT / path).resolve()


def ensure_data_directories() -> None:
    for path in [
        DATA_DIR,
        DATA_DIR / "drafts",
        DATA_DIR / "designs",
        DATA_DIR / "research_snapshots",
        DATA_DIR / "screenshots",
        DATA_DIR / "logs",
        DATA_DIR / "backups",
        DATA_DIR / "exports",
    ]:
        path.mkdir(parents=True, exist_ok=True)
