import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import aiosqlite
from aiogram import Bot

from database.db import DB_PATH, get_chat_settings
from services.steam_api import get_top_steam_deals


logger = logging.getLogger(__name__)

BISHKEK_TZ = ZoneInfo("Asia/Bishkek")


async def send_daily_digest(bot: Bot):
    """Проверяет чаты и отправляет дайджест, если наступило заданное время."""

    now_time = datetime.now(BISHKEK_TZ).strftime("%H:%M")
    logger.info("Проверка дайджеста: текущее время %s", now_time)

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT chat_id FROM chat_settings WHERE notify_time = ?",
            (now_time,),
        ) as cursor:
            rows = await cursor.fetchall()
            async with db.execute(
            "SELECT chat_id, notify_time FROM chat_settings"
            ) as cursor:
                all_rows = await cursor.fetchall()

            logger.info("Все настройки чатов в БД: %s", all_rows)
            logger.info("Чаты для дайджеста на %s: %s", now_time, rows)

        for row in rows:
            chat_id = row[0]

            try:
                settings = await get_chat_settings(chat_id)

                deals = await get_top_steam_deals(
                    min_discount=settings["min_discount"],
                    max_pages=1,
                )

                if not deals:
                    continue

                if settings["sort_by"] == "min_rating":
                    deals.reverse()

                deal = deals[0]

                text = (
                    f"📢 **Ежедневный дайджест скидок Steam** 🎮\n\n"
                    f"🎮 **{deal['title']}**\n"
                    f"💳 ~${deal['normal_price']}~ ➡️ "
                    f"**${deal['sale_price']}** "
                    f"(🔥 -{deal['discount']}%)\n\n"
                    f"🛒 [Купить в Steam]({deal['deal_link']})"
                )

                async with db.execute(
                    "SELECT message_id FROM daily_messages WHERE chat_id = ?",
                    (chat_id,),
                ) as cursor:
                    old_msg = await cursor.fetchone()

                if old_msg:
                    try:
                        await bot.delete_message(
                            chat_id=chat_id,
                            message_id=old_msg[0],
                        )
                    except Exception:
                        pass

                msg = await bot.send_photo(
                    chat_id=chat_id,
                    photo=deal["thumb"],
                    caption=text,
                    parse_mode="Markdown",
                )

                try:
                    await bot.pin_chat_message(
                        chat_id=chat_id,
                        message_id=msg.message_id,
                    )
                except Exception:
                    pass

                await db.execute(
                    """
                    INSERT INTO daily_messages (chat_id, message_id)
                    VALUES (?, ?)

                    ON CONFLICT(chat_id)
                    DO UPDATE SET message_id = excluded.message_id
                    """,
                    (chat_id, msg.message_id),
                )

                await db.commit()

            except Exception as e:
                logger.error(
                    "Не удалось отправить дайджест в чат %s: %s",
                    chat_id,
                    e,
                )