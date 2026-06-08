from pathlib import Path

import aiosqlite

from app.internal.config import get_settings

_conn: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _conn
    if _conn is None:
        settings = get_settings()
        settings.database_path.parent.mkdir(parents=True, exist_ok=True)
        _conn = await aiosqlite.connect(settings.database_path)
        _conn.row_factory = aiosqlite.Row
        await _conn.execute("PRAGMA journal_mode = WAL")
        await _conn.execute("PRAGMA foreign_keys = ON")
        await _conn.execute("PRAGMA synchronous = NORMAL")
    return _conn


async def close_db() -> None:
    global _conn
    if _conn is not None:
        await _conn.close()
        _conn = None


async def init_db() -> None:
    db = await get_db()
    migrations_dir = Path(__file__).parent / "migrations"
    for sql_file in sorted(migrations_dir.glob("*.sql")):
        sql = sql_file.read_text()
        await db.executescript(sql)
    await db.commit()
