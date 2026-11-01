#!/usr/bin/env python3
"""Convert a validated CSV into the admin panel's bulk-import file.

Usage:
    python scripts/to_excel.py items.csv items.xlsx

Writes .xlsx when openpyxl is installed; otherwise writes a UTF-8 CSV with BOM
(Excel opens it with Persian text intact) next to the requested name.
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import COLUMNS, read_csv  # noqa: E402


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    src, dst = sys.argv[1], Path(sys.argv[2])
    _, rows = read_csv(src)
    data = [[r.get(c, "") for c in COLUMNS] for r in rows]

    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font
    except ImportError:
        fallback = dst.with_suffix(".csv")
        with open(fallback, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(COLUMNS)
            w.writerows(data)
        print(f"openpyxl not installed; wrote {fallback} (opens in Excel)")
        return 0

    wb = Workbook()
    ws = wb.active
    ws.title = "items"
    ws.append(COLUMNS)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in data:
        ws.append(row)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for col in ws.columns:
        width = max(len(str(c.value or "")) for c in col)
        ws.column_dimensions[col[0].column_letter].width = min(max(10, width + 2), 60)
    try:
        wb.save(dst)
    except PermissionError:
        print(f"Cannot write {dst}: the file is open in another program (close it in Excel and run again).")
        return 1
    print(f"wrote {dst} ({len(data)} items)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
