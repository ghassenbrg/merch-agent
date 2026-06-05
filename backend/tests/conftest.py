import os
import tempfile
from pathlib import Path


TEST_DATA_DIR = Path(tempfile.mkdtemp(prefix="merch-agent-tests-"))
os.environ["MERCH_AGENT_DATA_DIR"] = str(TEST_DATA_DIR)

from app.db.database import init_database, seed_database


def pytest_configure() -> None:
    init_database()
    seed_database()
