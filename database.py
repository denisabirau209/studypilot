from __future__ import annotations

import aiosqlite

DB_PATH = "studypilot.db"


async def init_db():
    """Create tables if they don't exist. Called once at startup."""
    async with aiosqlite.connect(DB_PATH) as db:
        # SQLite ignores foreign keys unless explicitly enabled, per connection
        await db.execute("PRAGMA foreign_keys = ON")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS materii (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                nume     TEXT    NOT NULL,
                cod      TEXT,
                UNIQUE(guild_id, nume)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS deadlines (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id   INTEGER NOT NULL,
                materie_id INTEGER NOT NULL,
                titlu      TEXT    NOT NULL,
                data       TEXT    NOT NULL,  -- ISO 8601, so text sorting is chronological
                added_by   INTEGER NOT NULL,
                notif_7d   INTEGER DEFAULT 0,  -- idempotency flags: prevent duplicate
                notif_2d   INTEGER DEFAULT 0,  -- reminders after a restart
                notif_12h  INTEGER DEFAULT 0,
                FOREIGN KEY (materie_id) REFERENCES materii(id) ON DELETE CASCADE
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                guild_id            INTEGER PRIMARY KEY,
                reminder_channel_id INTEGER
            )
        """)

        await db.commit()


# subjects

async def add_materie(guild_id: int, nume: str, cod: str | None = None) -> int | None:
    """Add a subject. Returns its id, or None if it already exists."""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            cursor = await db.execute(
                "INSERT INTO materii (guild_id, nume, cod) VALUES (?, ?, ?)",
                (guild_id, nume, cod)
            )
            await db.commit()
            return cursor.lastrowid
        except aiosqlite.IntegrityError:
            return None


async def get_subjects(guild_id: int) -> list[dict]:
    """All subjects for a guild, alphabetically."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row  # access columns by name instead of index
        cursor = await db.execute(
            "SELECT * FROM materii WHERE guild_id = ? ORDER BY nume",
            (guild_id,)
        )
        return [dict(r) for r in await cursor.fetchall()]


async def get_subjects_by_nume(guild_id: int, nume: str) -> dict | None:
    """Look up a subject by exact name. None if not found."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM materii WHERE guild_id = ? AND nume = ?",
            (guild_id, nume)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


# deadlines

async def add_deadline(guild_id: int, materie_id: int, titlu: str,
                       data: str, added_by: int) -> int:
    """Add a deadline. Date must be YYYY-MM-DD."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO deadlines (guild_id, materie_id, titlu, data, added_by)
               VALUES (?, ?, ?, ?, ?)""",
            (guild_id, materie_id, titlu, data, added_by)
        )
        await db.commit()
        return cursor.lastrowid


async def get_deadlines(guild_id: int, doar_viitoare: bool = True) -> list[dict]:
    """Deadlines for a guild, with the subject name joined in."""
    # The JOIN avoids an N+1 query: one call instead of one per deadline.
    query = """
        SELECT d.*, m.nume AS materie
        FROM deadlines d
        JOIN materii m ON d.materie_id = m.id
        WHERE d.guild_id = ?
    """
    if doar_viitoare:
        query += " AND d.data >= date('now')"
    query += " ORDER BY d.data"

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query, (guild_id,))
        return [dict(r) for r in await cursor.fetchall()]


async def delete_deadline(guild_id: int, deadline_id: int) -> bool:
    """Delete a deadline. True if one was removed, False if not found."""
    async with aiosqlite.connect(DB_PATH) as db:
        # guild_id in the WHERE acts as an authorization check:
        # knowing an id from another server isn't enough to delete it
        cursor = await db.execute(
            "DELETE FROM deadlines WHERE id = ? AND guild_id = ?",
            (deadline_id, guild_id)
        )
        await db.commit()
        return cursor.rowcount > 0


# settings

async def set_reminder_channel(guild_id: int, channel_id: int):
    """Set the channel reminders are posted to. Insert or update in one atomic call."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO settings (guild_id, reminder_channel_id) VALUES (?, ?)
               ON CONFLICT(guild_id) DO UPDATE SET reminder_channel_id = ?""",
            (guild_id, channel_id, channel_id)
        )
        await db.commit()


async def get_reminder_channel(guild_id: int) -> int | None:
    """Configured channel id, or None if the guild hasn't set one up."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT reminder_channel_id FROM settings WHERE guild_id = ?",
            (guild_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None