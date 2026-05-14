import gspread
from src.config import MONTH_NAMES, DATA_START_ROW, DATA_END_ROW, COL_DATE, COL_CLASS3, COL_CLASS4
from src.sheets.client import get_spreadsheet, sheet_mutex


def get_worksheet_for_date(date_str: str, spreadsheet_id: str) -> gspread.Worksheet:
    """Return the worksheet whose C5 cell matches the month in date_str (DD/MM/YY)."""
    month_num = int(date_str.split("/")[1])
    month_name = MONTH_NAMES[month_num - 1]
    spreadsheet = get_spreadsheet(spreadsheet_id)
    for ws in spreadsheet.worksheets():
        if ws.title in ("main", "Template"):
            continue
        try:
            c5 = ws.acell("C5").value or ""
            if c5.strip().lower() == month_name.lower():
                return ws
        except Exception:
            continue
    raise ValueError(
        f"No worksheet found for month '{month_name}' (checked C5 of each tab). "
        f"Available tabs: {[ws.title for ws in spreadsheet.worksheets()]}"
    )


def next_empty_row(worksheet: gspread.Worksheet) -> tuple[int, int]:
    """Return (sheet_row, sn) of the first empty entry slot."""
    col_index = _col_letter_to_index(COL_DATE)
    date_col = worksheet.col_values(col_index)

    for row_num in range(DATA_START_ROW, DATA_END_ROW + 1):
        cell_index = row_num - 1  # col_values is 0-indexed
        value = date_col[cell_index] if cell_index < len(date_col) else ""
        if not value.strip():
            sn = row_num - DATA_START_ROW + 1
            return row_num, sn

    raise ValueError(
        f"Month is full — all rows {DATA_START_ROW}–{DATA_END_ROW} are occupied. "
        "Cannot add more entries."
    )


def get_month_totals(date_str: str, spreadsheet_id: str) -> dict[str, int]:
    """Return {'class3': total_km, 'class4': total_km} for the month in date_str."""
    with sheet_mutex:
        ws = get_worksheet_for_date(date_str, spreadsheet_id)
        col3_idx = _col_letter_to_index(COL_CLASS3)
        col4_idx = _col_letter_to_index(COL_CLASS4)

        col3_values = ws.col_values(col3_idx)
        col4_values = ws.col_values(col4_idx)

        def _sum_range(values: list[str]) -> int:
            total = 0
            for i in range(DATA_START_ROW - 1, DATA_END_ROW):
                if i < len(values):
                    try:
                        total += int(values[i])
                    except (ValueError, TypeError):
                        pass
            return total

        return {
            "class3": _sum_range(col3_values),
            "class4": _sum_range(col4_values),
        }


def get_all_totals(spreadsheet_id: str) -> list[dict]:
    """Return totals for every worksheet whose C5 matches a month label (same rule as month tabs)."""
    with sheet_mutex:
        spreadsheet = get_spreadsheet(spreadsheet_id)
        results = []

        def _sum_col(values: list[str]) -> int:
            total = 0
            for j in range(DATA_START_ROW - 1, DATA_END_ROW):
                if j < len(values):
                    try:
                        total += int(values[j])
                    except (ValueError, TypeError):
                        pass
            return total

        col3_idx = _col_letter_to_index(COL_CLASS3)
        col4_idx = _col_letter_to_index(COL_CLASS4)

        for ws in spreadsheet.worksheets():
            if ws.title in ("main", "Template"):
                continue
            try:
                c5 = (ws.acell("C5").value or "").strip()
            except Exception:
                continue
            if not c5:
                continue

            month_index = None
            for i, name in enumerate(MONTH_NAMES):
                if c5.lower() == name.lower():
                    month_index = i
                    break
            if month_index is None:
                continue

            try:
                col3 = ws.col_values(col3_idx)
                col4 = ws.col_values(col4_idx)
            except Exception:
                continue

            title = (ws.title or "").strip()
            if title.isdigit():
                tab_sort = int(title)
            else:
                tab_sort = 1_000_000
            label = f"{c5} ({ws.title})"

            results.append({
                "month": label,
                "month_index": month_index,
                "tab_sort": tab_sort,
                "class3": _sum_col(col3),
                "class4": _sum_col(col4),
            })

        results.sort(key=lambda r: (r["tab_sort"], r["month_index"]))
        for r in results:
            r.pop("tab_sort", None)
            r.pop("month_index", None)
        return results


def _col_letter_to_index(letter: str) -> int:
    """Convert column letter (A=1, B=2, …) to 1-based index."""
    result = 0
    for ch in letter.upper():
        result = result * 26 + (ord(ch) - ord("A") + 1)
    return result
