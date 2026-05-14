import threading

import gspread
from google.oauth2.service_account import Credentials
from src.config import GOOGLE_CREDS_PATH

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

_client: gspread.Client | None = None
_spreadsheet_cache: dict[str, gspread.Spreadsheet] = {}

_client_lock = threading.Lock()
_cache_lock = threading.Lock()
sheet_mutex = threading.Lock()


def _ensure_client() -> gspread.Client:
    global _client
    if _client is not None:
        return _client
    with _client_lock:
        if _client is None:
            creds = Credentials.from_service_account_file(GOOGLE_CREDS_PATH, scopes=_SCOPES)
            _client = gspread.authorize(creds)
        return _client


def get_spreadsheet(spreadsheet_id: str) -> gspread.Spreadsheet:
    """Return a cached Spreadsheet handle for this ID (owned by the service account client)."""
    with _cache_lock:
        cached = _spreadsheet_cache.get(spreadsheet_id)
        if cached is not None:
            return cached
        ss = _ensure_client().open_by_key(spreadsheet_id)
        _spreadsheet_cache[spreadsheet_id] = ss
        return ss


def validate_spreadsheet_access(spreadsheet_id: str) -> None:
    """Raises if the service account cannot open the spreadsheet."""
    _ = get_spreadsheet(spreadsheet_id).title
