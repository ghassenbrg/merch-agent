from __future__ import annotations

import argparse
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.local_operations import restore_local_package_export


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Restore a local package export. Current data is backed up by default."
    )
    parser.add_argument("export_path", type=Path)
    parser.add_argument("--force", action="store_true", help="Required safety flag.")
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip the pre-restore SQLite backup. Use only when data loss is intentional.",
    )
    args = parser.parse_args()
    try:
        result = restore_local_package_export(
            args.export_path,
            force=args.force,
            backup=not args.no_backup,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(f"database={result['database']}")
    print(f"backup={result['backup']}")


if __name__ == "__main__":
    main()
