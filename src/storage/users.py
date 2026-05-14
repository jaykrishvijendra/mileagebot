import json
import re
from pathlib import Path

import aiosqlite

from src.config import GOOGLE_CREDS_PATH

DB_PATH = Path("data/log.db")

_email_cache: str | None = None


def service_account_email() -> str:
    global _email_cache
    if _email_cache is None:
        data = json.loads(Path(GOOGLE_CREDS_PATH).read_text(encoding="utf-8"))
        _email_cache = data["client_email"]
    return _email_cache


def parse_spreadsheet_id(text: str) -> str | None:
    """Extract spreadsheet ID from a Google Sheets URL or a raw ID string."""
    text = text.strip()
    if not text:
        return None
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", text)
    if m:
        return m.group(1)
    if re.fullmatch(r"[a-zA-Z0-9_-]{30,}", text):
        return text
    return None


async def _ensure_user_schema(db: aiosqlite.Connection) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            spreadsheet_id TEXT NOT NULL
        )
    """)
    await db.commit()


async def get_spreadsheet_id(user_id: int) -> str | None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_user_schema(db)
        async with db.execute(
            "SELECT spreadsheet_id FROM user_settings WHERE user_id=?",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


async def set_spreadsheet_id(user_id: int, spreadsheet_id: str) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_user_schema(db)
        await db.execute(
            """INSERT INTO user_settings (user_id, spreadsheet_id)
               VALUES (?, ?)
               ON CONFLICT(user_id) DO UPDATE SET spreadsheet_id=excluded.spreadsheet_id""",
            (user_id, spreadsheet_id),
        )
        await db.commit()
