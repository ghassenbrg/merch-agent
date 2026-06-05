from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.database import init_database, seed_database


def main() -> None:
    init_database()
    seed_database()
    print("seeded=true")


if __name__ == "__main__":
    main()
