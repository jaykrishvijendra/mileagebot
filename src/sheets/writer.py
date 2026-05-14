import asyncio
import threading

from src.config import COL_SN, COL_START, COL_END, COL_CLASS3, COL_CLASS4
from src.models.entry import Entry
from src.sheets.client import sheet_mutex
from src.sheets.reader import get_worksheet_for_date, next_empty_row, get_month_totals

_dict_lock = threading.Lock()
_write_locks: dict[int, asyncio.Lock] = {}


def _write_lock_for(user_id: int) -> asyncio.Lock:
    with _dict_lock:
        if user_id not in _write_locks:
            _write_locks[user_id] = asyncio.Lock()
        return _write_locks[user_id]


def _write_entry_sync(entry: Entry, spreadsheet_id: str) -> tuple[int, int]:
    with sheet_mutex:
        ws = get_worksheet_for_date(entry.date_str, spreadsheet_id)
        row, sn = next_empty_row(ws)

        class3_km = entry.mileage if entry.vehicle_class == 3 else ""
        class4_km = entry.mileage if entry.vehicle_class == 4 else ""

        start_val = entry.odo_start if entry.odo_start is not None else ""
        end_val = entry.odo_end if entry.odo_end is not None else ""

        ws.update(
            [[sn, entry.date_str, entry.vehicle, start_val, end_val, class3_km, class4_km]],
            f"{COL_SN}{row}:{COL_CLASS4}{row}",
        )
        return row, sn


def _write_entry_and_totals_sync(entry: Entry, spreadsheet_id: str) -> tuple[int, int, dict[str, int]]:
    """Same thread as write + month totals — avoids overlapping gspread use across pool workers."""
    row, sn = _write_entry_sync(entry, spreadsheet_id)
    totals = get_month_totals(entry.date_str, spreadsheet_id)
    return row, sn, totals


async def write_entry_and_totals(
    entry: Entry, spreadsheet_id: str, user_id: int
) -> tuple[int, int, dict[str, int]]:
    """Write entry and return running month totals (one thread hop)."""
    lock = _write_lock_for(user_id)
    async with lock:
        return await asyncio.to_thread(_write_entry_and_totals_sync, entry, spreadsheet_id)
