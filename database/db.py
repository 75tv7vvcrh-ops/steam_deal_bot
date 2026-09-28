import logging
from pathlib import Path

import aiosqlite


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "steam_bot.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id INTEGER PRIMARY KEY,
                notify_time TEXT DEFAULT '10:00',
                min_discount INTEGER DEFAULT 30,
                sort_by TEXT DEFAULT 'max_rating'
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS daily_messages (
                chat_id INTEGER PRIMARY KEY,
                message_id INTEGER NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS wishlist (
                user_id INTEGER,
                deal_id TEXT,
                title TEXT,
                sale_price TEXT,
                normal_price TEXT,
                discount INTEGER,
                thumb TEXT,
                deal_link TEXT,
                PRIMARY KEY (user_id, deal_id)
            )
        """)

        await db.commit()

    logging.info("База данных успешно инициализирована.")


async def get_chat_settings(chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT notify_time, min_discount, sort_by
            FROM chat_settings
            WHERE chat_id = ?
            """,
            (chat_id,),
        ) as cursor:
            row = await cursor.fetchone()

            if row:
                return {
                    "notify_time": row[0],
                    "min_discount": row[1],
                    "sort_by": row[2] or "max_rating",
                }

            return {
                "notify_time": "10:00",
                "min_discount": 30,
                "sort_by": "max_rating",
            }


async def update_chat_settings(
    chat_id: int,
    notify_time: str = None,
    min_discount: int = None,
    sort_by: str = None,
):
    current = await get_chat_settings(chat_id)

    new_time = (
        notify_time
        if notify_time is not None
        else current["notify_time"]
    )

    new_discount = (
        min_discount
        if min_discount is not None
        else current["min_discount"]
    )

    new_sort = (
        sort_by
        if sort_by is not None
        else current["sort_by"]
    )

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO chat_settings (
                chat_id,
                notify_time,
                min_discount,
                sort_by
            )
            VALUES (?, ?, ?, ?)

            ON CONFLICT(chat_id)
            DO UPDATE SET
                notify_time = excluded.notify_time,
                min_discount = excluded.min_discount,
                sort_by = excluded.sort_by
            """,
            (
                chat_id,
                new_time,
                new_discount,
                new_sort,
            ),
        )

        await db.commit()


# --- WISHLIST ---


async def add_to_wishlist(user_id: int, deal: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO wishlist (
                user_id,
                deal_id,
                title,
                sale_price,
                normal_price,
                discount,
                thumb,
                deal_link
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(user_id, deal_id)
            DO NOTHING
            """,
            (
                user_id,
                deal["deal_id"],
                deal["title"],
                deal["sale_price"],
                deal["normal_price"],
                deal["discount"],
                deal["thumb"],
                deal["deal_link"],
            ),
        )

        await db.commit()


async def remove_from_wishlist(user_id: int, deal_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            DELETE FROM wishlist
            WHERE user_id = ? AND deal_id = ?
            """,
            (user_id, deal_id),
        )

        await db.commit()


async def get_wishlist(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT
                deal_id,
                title,
                sale_price,
                normal_price,
                discount,
                thumb,
                deal_link
            FROM wishlist
            WHERE user_id = ?
            """,
            (user_id,),
        ) as cursor:
            rows = await cursor.fetchall()

            return [
                {
                    "deal_id": row[0],
                    "title": row[1],
                    "sale_price": row[2],
                    "normal_price": row[3],
                    "discount": row[4],
                    "thumb": row[5],
                    "deal_link": row[6],
                }
                for row in rows
            ]


async def is_in_wishlist(user_id: int, deal_id: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT 1
            FROM wishlist
            WHERE user_id = ? AND deal_id = ?
            """,
            (user_id, deal_id),
        ) as cursor:
            return await cursor.fetchone() is not None