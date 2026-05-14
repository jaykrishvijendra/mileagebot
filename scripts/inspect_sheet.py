"""
Run this before starting the bot to confirm the sheet structure.
Usage: python scripts/inspect_sheet.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from src.config import SPREADSHEET_ID
from src.sheets.client import get_spreadsheet


def main():
    if not SPREADSHEET_ID:
        print("Set SPREADSHEET_ID in .env for this script (inspect_sheet uses one workbook).")
        sys.exit(1)
    ss = get_spreadsheet(SPREADSHEET_ID)
    print(f"Spreadsheet: {ss.title}")
    print(f"ID: {ss.id}\n")

    worksheets = ss.worksheets()
    print(f"Tabs ({len(worksheets)}) — showing C5/D5 (month label):")
    for ws in worksheets:
        try:
            c5 = ws.acell("C5").value or ""
            d5 = ws.acell("D5").value or ""
            label = f"C5={c5!r}  D5={d5!r}"
        except Exception as e:
            label = f"(error reading: {e})"
        print(f"  [{ws.title:>3}] {label}")

    print()
    # Inspect tab '1' in detail as a sample
    target = next((ws for ws in worksheets if ws.title == "1"), worksheets[0])
    print(f"Inspecting tab: {target.title!r} — first 35 rows:")
    rows = target.get_all_values()
    for i, row in enumerate(rows[:35], start=1):
        non_empty = [(j + 1, v) for j, v in enumerate(row) if str(v).strip()]
        if non_empty:
            print(f"  Row {i:2d}: {non_empty}")


if __name__ == "__main__":
    main()
