import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from database.db import init_db
from handlers.private import router as private_router
from handlers.group import router as group_router
from services.scheduler import send_daily_digest

# Загружаем переменные окружения из файла .env
load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")  # Убедись, что в твоем .env файле переменная называется BOT_TOKEN

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    logger = logging.getLogger(__name__)
    
    if not API_TOKEN:
        logger.error("Не найден токен бота! Проверь файл .env (переменная BOT_TOKEN).")
        return

    logger.info("Запуск Telegram-бота...")

    # Инициализация БД
    await init_db()

    bot = Bot(token=API_TOKEN)
    dp = Dispatcher()

    from aiogram.types import BotCommand
    await bot.set_my_commands([
        BotCommand(command="deals", description="🔥 Посмотреть горячие скидки"),
        BotCommand(command="random", description="🎲 Случайная скидка"),
        BotCommand(command="search", description="🔍 Найти игру по названию"),
        BotCommand(command="settings", description="⚙️ Настройки (для админов в группах)"),
        BotCommand(command="donate", description="💖 Поддержать проект"),
        BotCommand(command="test_digest", description="📢 Тест дайджеста (для админов)")
    ])
    
    # Подключаем роутеры (ЛС и Группы)
    dp.include_router(private_router)
    dp.include_router(group_router)

    # Настройка планировщика APScheduler
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(send_daily_digest, "interval", minutes=1, args=(bot,))
    scheduler.start()

    # Пропуск накопившихся апдейтов и старт поллинга
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")