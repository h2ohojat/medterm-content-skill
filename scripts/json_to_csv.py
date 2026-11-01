#!/usr/bin/env python3
"""Convert drafted items from JSON to the import CSV, so columns can never shift.

Usage:
    python scripts/json_to_csv.py items.json items.csv

items.json is a list of objects whose keys are column names from reference/columns.md.
Missing keys become empty cells; unknown keys are reported and the file is not written.
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import COLUMNS  # noqa: E402


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    items = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if isinstance(items, dict):
        items = items.get("items", [])
    unknown = sorted({k for it in items for k in it if k not in COLUMNS})
    if unknown:
        print("Unknown keys (fix the names, see reference/columns.md): " + ", ".join(unknown))
        return 1
    with open(sys.argv[2], "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for it in items:
            w.writerow([str(it.get(c, "") if it.get(c) is not None else "").strip() for c in COLUMNS])
    print(f"wrote {sys.argv[2]} ({len(items)} items, {len(COLUMNS)} columns)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
