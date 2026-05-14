import aiosqlite
from pathlib import Path

DB_PATH = Path("data/log.db")


async def _ensure_entries_schema(db: aiosqlite.Connection) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            date_str    TEXT NOT NULL,
            vehicle     TEXT NOT NULL,
            vehicle_class INTEGER NOT NULL,
            odo_start   INTEGER,
            odo_end     INTEGER,
            mileage     INTEGER,
            sheet_row   INTEGER,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await db.commit()


async def log_entry(user_id: int, entry, sheet_row: int) -> int:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_entries_schema(db)
        cursor = await db.execute(
            """INSERT INTO entries
               (user_id, date_str, vehicle, vehicle_class, odo_start, odo_end, mileage, sheet_row)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, entry.date_str, entry.vehicle, entry.vehicle_class,
             entry.odo_start, entry.odo_end, entry.mileage, sheet_row),
        )
        await db.commit()
        return cursor.lastrowid
