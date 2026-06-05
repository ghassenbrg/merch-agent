from __future__ import annotations

import argparse
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.database import init_database
from app.services.local_operations import export_local_packages


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export local draft packages for backup or offline inspection."
    )
    parser.add_argument(
        "--draft-id",
        action="append",
        dest="draft_ids",
        help="Limit export to a draft id. Repeat for multiple drafts.",
    )
    args = parser.parse_args()
    init_database()
    export_path = export_local_packages(args.draft_ids)
    print(f"export={export_path}")


if __name__ == "__main__":
    main()
