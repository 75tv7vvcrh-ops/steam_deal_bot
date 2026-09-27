import aiosqlite
import logging
from datetime import datetime
from aiogram import Bot
from database.db import DB_PATH, get_chat_settings
from services.steam_api import get_top_steam_deals

logger = logging.getLogger(__name__)

async def send_daily_digest(bot: Bot):
    """Проверяет каждую минуту, у каких чатов наступило время рассылки"""
    # Получаем текущее время в формате "ЧЧ:ММ" (например, "10:00")
    now_time = datetime.now().strftime("%H:%M")
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Выбираем только те чаты, у которых notify_time совпадает с текущей минутой
        async with db.execute("SELECT chat_id FROM chat_settings WHERE notify_time = ?", (now_time,)) as cursor:
            rows = await cursor.fetchall()
            
            for row in rows:
                chat_id = row[0]
                try:
                    settings = await get_chat_settings(chat_id)
                    deals = await get_top_steam_deals(min_discount=settings["min_discount"], max_pages=1)
                    
                    if not deals:
                        continue
                    
                    if settings["sort_by"] == "min_rating":
                        deals.reverse()

                    deal = deals[0]
                    text = (
                        f"📢 **Ежедневный дайджест скидок Steam** 🎮\n\n"
                        f"🎮 **{deal['title']}**\n"
                        f"💳 ~${deal['normal_price']}~ ➡️ **${deal['sale_price']}** (🔥 -{deal['discount']}%)\n\n"
                        f"🛒 [Купить в Steam]({deal['deal_link']})"
                    )

                    # 1. Удаляем старое сообщение дайджеста, если оно было
                    async with db.execute("SELECT message_id FROM daily_messages WHERE chat_id = ?", (chat_id,)) as cur:
                        old_msg = await cur.fetchone()
                        if old_msg:
                            try:
                                await bot.delete_message(chat_id=chat_id, message_id=old_msg[0])
                            except Exception:
                                pass

                    # 2. Отправляем новое фото
                    msg = await bot.send_photo(
                        chat_id=chat_id,
                        photo=deal['thumb'],
                        caption=text,
                        parse_mode="Markdown"
                    )

                    # 3. Закрепляем (если есть права)
                    try:
                        await bot.pin_chat_message(chat_id=chat_id, message_id=msg.message_id)
                    except Exception:
                        pass

                    # 4. Сохраняем ID нового сообщения
                    await db.execute(
                        """
                        INSERT INTO daily_messages (chat_id, message_id) VALUES (?, ?)
                        ON CONFLICT(chat_id) DO UPDATE SET message_id = excluded.message_id
                        """,
                        (chat_id, msg.message_id)
                    )
                    await db.commit()

                except Exception as e:
                    logger.error(f"Не удалось отправить дайджест в чат {chat_id}: {e}")