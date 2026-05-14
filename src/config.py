import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GOOGLE_CREDS_PATH = os.environ["GOOGLE_CREDS_PATH"]

# Optional: used only by scripts/inspect_sheet.py (each Telegram user has their own sheet via /register).
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Sheet layout constants (confirmed from inspect_sheet.py)
DATA_START_ROW = 9    # first entry row — S/N 1 is at row 9 (after 8 header rows)
DATA_END_ROW = 36     # last entry row — S/N 28 at row 36
COL_SN = "A"
COL_DATE = "B"
COL_VEHICLE = "C"
COL_START = "D"
COL_END = "E"
COL_CLASS3 = "F"
COL_CLASS4 = "G"
