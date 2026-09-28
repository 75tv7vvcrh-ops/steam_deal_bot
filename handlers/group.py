import random
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, 
    LabeledPrice, PreCheckoutQuery, InputMediaPhoto
)
from database.db import get_chat_settings, update_chat_settings
from services.steam_api import get_top_steam_deals, search_deals_by_title

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

# Временный кэш списков игр групп
GROUP_DEALS_CACHE = {}


async def is_admin(message: Message) -> bool:
    if message.from_user is None:
        return False
    member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    return member.status in ("creator", "administrator")


# =====================================================================
# КЛАВИАТУРЫ ДЛЯ ГРУППЫ
# =====================================================================

def build_group_settings_keyboard(current_discount: int, current_time: str, current_sort: str):
    discounts = [30, 50, 70, 80]
    times = ["09:00", "12:00", "18:00", "21:00"]
    
    buttons = []
    
    discount_row = [
        InlineKeyboardButton(
            text=f"✅ {d}%" if d == current_discount else f"{d}%", 
            callback_data=f"grp_set_disc:{d}"
        ) for d in discounts
    ]
    
    btn_max = f"✅ 🔥 Макс. рейтинг" if current_sort == "max_rating" else "🔥 Макс. рейтинг"
    btn_min = f"✅ 📉 Мин. рейтинг" if current_sort == "min_rating" else "📉 Мин. рейтинг"
    sort_row = [
        InlineKeyboardButton(text=btn_max, callback_data="grp_set_sort:max_rating"),
        InlineKeyboardButton(text=btn_min, callback_data="grp_set_sort:min_rating")
    ]
    
    time_row = [
        InlineKeyboardButton(
            text=f"✅ {t}" if t == current_time else f"{t}", 
            callback_data=f"grp_set_time:{t}"
        ) for t in times
    ]
        
    buttons.append([InlineKeyboardButton(text="── 🎯 Мин. скидка ──", callback_data="grp_ignore")])
    buttons.append(discount_row)
    buttons.append([InlineKeyboardButton(text="── 📊 Порядок рейтинга ──", callback_data="grp_ignore")])
    buttons.append(sort_row)
    buttons.append([InlineKeyboardButton(text="── ⏰ Время дайджеста ──", callback_data="grp_ignore")])
    buttons.append(time_row)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def build_group_deal_card(deals: list, index: int = 0):
    deal = deals[index]
    total = len(deals)
    
    text = (
        f"🎮 **{deal['title']}**\n\n"
        f"💳 Старая цена: ~${deal['normal_price']}~\n"
        f"🔥 **Скидка:** {deal['discount']}%\n"
        f"✅ **Новая цена:** ${deal['sale_price']}\n\n"
        f"📌 *Игра {index + 1} из {total}*"
    )
    
    buttons = [
        [InlineKeyboardButton(text="🛒 Купить в Steam", url=deal['deal_link'])]
    ]
    
    nav_buttons = []
    if index > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"grp_page:{index - 1}"))
    if index < total - 1:
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"grp_page:{index + 1}"))
        
    if nav_buttons:
        buttons.append(nav_buttons)
        
    return deal['thumb'], text, InlineKeyboardMarkup(inline_keyboard=buttons)


# =====================================================================
# КОМАНДЫ ДЛЯ ВСЕХ ПОЛЬЗОВАТЕЛЕЙ В ГРУППЕ
# =====================================================================

@router.message(Command("deals"))
async def group_deals(message: Message):
    await message.answer("🔍 Ищу актуальные скидки для группы...")
    
    settings = await get_chat_settings(message.chat.id)
    deals = await get_top_steam_deals(min_discount=settings["min_discount"], max_pages=3)
    
    if not deals:
        await message.answer("К сожалению, скидок по фильтру группы не найдено.")
        return

    if settings["sort_by"] == "min_rating":
        deals.reverse()

    GROUP_DEALS_CACHE[message.chat.id] = deals
    image_url, text, keyboard = await build_group_deal_card(deals, index=0)
    await message.answer_photo(photo=image_url, caption=text, reply_markup=keyboard, parse_mode="Markdown")


@router.message(Command("random"))
async def group_random_deal(message: Message):
    settings = await get_chat_settings(message.chat.id)
    deals = await get_top_steam_deals(min_discount=settings["min_discount"], max_pages=3)
    
    if not deals:
        await message.answer("Не удалось найти скидки.")
        return

    if settings["sort_by"] == "min_rating":
        deals.reverse()

    GROUP_DEALS_CACHE[message.chat.id] = deals
    random_index = random.randint(0, len(deals) - 1)
    image_url, text, keyboard = await build_group_deal_card(deals, index=random_index)
    
    await message.answer("🎰 **Случайная скидка для чата:**", parse_mode="Markdown")
    await message.answer_photo(photo=image_url, caption=text, reply_markup=keyboard, parse_mode="Markdown")


@router.message(Command("search"))
async def group_search(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Пожалуйста, укажите название игры.\nПример: `/search Cyberpunk`", parse_mode="Markdown")
        return

    query = args[1]
    await message.answer(f"🔍 Ищу по запросу **«{query}»**...", parse_mode="Markdown")
    
    deals = await search_deals_by_title(query)
    if not deals:
        await message.answer(f"По запросу «{query}» ничего не найдено.")
        return

    GROUP_DEALS_CACHE[message.chat.id] = deals
    image_url, text, keyboard = await build_group_deal_card(deals, index=0)
    await message.answer_photo(photo=image_url, caption=text, reply_markup=keyboard, parse_mode="Markdown")


@router.message(Command("donate"))
async def group_donate(message: Message):
    buttons = [
        [
            InlineKeyboardButton(text="⭐ 50 Stars", callback_data="grp_donate:50"),
            InlineKeyboardButton(text="⭐ 100 Stars", callback_data="grp_donate:100"),
        ],
        [
            InlineKeyboardButton(text="⭐ 250 Stars", callback_data="grp_donate:250"),
            InlineKeyboardButton(text="⭐ 500 Stars", callback_data="grp_donate:500"),
        ]
    ]
    await message.answer(
        "💖 **Поддержка проекта**\n\n"
        "Бот бесплатен для групп!\n"
        "Вы можете поддержать разработчика Telegram Звёздами:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown"
    )


@router.callback_query(lambda c: c.data and c.data.startswith("grp_donate:"))
async def group_process_donate(callback: CallbackQuery):
    amount = int(callback.data.split(":")[1])
    await callback.message.answer_invoice(
        title="Поддержка Steam Sales Bot",
        description=f"Донат {amount} Telegram Stars на развитие бота.",
        payload=f"donate_group_{amount}_stars",
        currency="XTR",
        prices=[LabeledPrice(label="Донат", amount=amount)]
    )
    await callback.answer()


@router.pre_checkout_query()
async def group_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(lambda m: m.successful_payment is not None)
async def group_successful_payment(message: Message):
    stars = message.successful_payment.total_amount
    await message.answer(f"🎉 **Спасибо!** Донат чата в размере {stars} ⭐ успешно получен!", parse_mode="Markdown")


# Пагинация для карточек в группе
@router.callback_query(lambda c: c.data and c.data.startswith("grp_page:"))
async def group_process_page(callback: CallbackQuery):
    target_index = int(callback.data.split(":")[1])
    chat_id = callback.message.chat.id
    
    deals = GROUP_DEALS_CACHE.get(chat_id, [])
    if not deals or target_index < 0 or target_index >= len(deals):
        await callback.answer("Сессия устарела. Введите /deals заново.", show_alert=True)
        return

    image_url, text, keyboard = await build_group_deal_card(deals, index=target_index)
    
    try:
        await callback.message.edit_media(
            media=InputMediaPhoto(media=image_url, caption=text, parse_mode="Markdown"),
            reply_markup=keyboard
        )
    except Exception:
        pass
        
    await callback.answer()


# =====================================================================
# АДМИНСКИЕ КОМАНДЫ (НАСТРОЙКИ И ТЕСТЫ)
# =====================================================================

@router.message(Command("settings"))
async def group_settings(message: Message):
    if not await is_admin(message):
        await message.answer("⚠️ Изменять настройки бота могут только администраторы чата.")
        return

    settings = await get_chat_settings(message.chat.id)
    keyboard = build_group_settings_keyboard(
        settings["min_discount"], 
        settings["notify_time"], 
        settings["sort_by"]
    )
    sort_title = "🔥 Макс. рейтинг" if settings["sort_by"] == "max_rating" else "📉 Мин. рейтинг"

    await message.answer(
        f"⚙️ **Настройки группы Steam Bot**\n\n"
        f"🔥 Мин. скидка: **от {settings['min_discount']}%**\n"
        f"📊 Порядок рейтинга: **{sort_title}**\n"
        f"⏰ Время дайджеста: **{settings['notify_time']}**\n\n"
        f"Выберите параметр для изменения:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.callback_query(lambda c: c.data and (c.data.startswith("grp_set_disc:") or c.data.startswith("grp_set_sort:") or c.data.startswith("grp_set_time:")))
async def group_settings_callback(callback: CallbackQuery):
    member = await callback.bot.get_chat_member(callback.message.chat.id, callback.from_user.id)
    if member.status not in ("creator", "administrator"):
        await callback.answer("⚠️ Только администраторы могут менять настройки.", show_alert=True)
        return

    chat_id = callback.message.chat.id
    data = callback.data

    if data.startswith("grp_set_disc:"):
        new_disc = int(data.split(":")[1])
        await update_chat_settings(chat_id, min_discount=new_disc)
        await callback.answer(f"Порог изменён на {new_disc}%")
    elif data.startswith("grp_set_sort:"):
        new_sort = data.split(":")[1]
        await update_chat_settings(chat_id, sort_by=new_sort)
        title = "Макс. рейтинг" if new_sort == "max_rating" else "Мин. рейтинг"
        await callback.answer(f"Порядок изменен на: {title}")
    elif data.startswith("grp_set_time:"):
        new_time = data.split(":", 1)[1]
        await update_chat_settings(chat_id, notify_time=new_time)
        await callback.answer(f"Время рассылки изменено на {new_time}")

    settings = await get_chat_settings(chat_id)
    keyboard = build_group_settings_keyboard(settings["min_discount"], settings["notify_time"], settings["sort_by"])
    sort_title = "🔥 Макс. рейтинг" if settings["sort_by"] == "max_rating" else "📉 Мин. рейтинг"

    try:
        await callback.message.edit_text(
            f"⚙️ **Настройки группы Steam Bot**\n\n"
            f"🔥 Мин. скидка: **от {settings['min_discount']}%**\n"
            f"📊 Порядок рейтинга: **{sort_title}**\n"
            f"⏰ Время дайджеста: **{settings['notify_time']}**\n\n"
            f"✅ Настройки успешно обновлены!",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except Exception:
        pass


@router.callback_query(lambda c: c.data == "grp_ignore")
async def group_ignore(callback: CallbackQuery):
    await callback.answer()


@router.message(Command("test_digest"))
async def group_test_digest(message: Message):
    if not await is_admin(message):
        await message.answer("⚠️ Команда доступна только администраторам.")
        return

    await message.answer("🔄 Генерирую тестовый дайджест...")
    settings = await get_chat_settings(message.chat.id)
    deals = await get_top_steam_deals(min_discount=settings["min_discount"], max_pages=1)

    if not deals:
        await message.answer("Скидок по фильтру не найдено.")
        return

    if settings["sort_by"] == "min_rating":
        deals.reverse()

    deal = deals[0]
    text = (
        f"🔥 **Тестовый дайджест для группы!**\n\n"
        f"🎮 **{deal['title']}**\n"
        f"💳 Старая цена: ~${deal['normal_price']}~\n"
        f"🔥 **Скидка:** {deal['discount']}%\n"
        f"✅ **Новая цена:** ${deal['sale_price']}\n\n"
        f"🛒 [Купить в Steam]({deal['deal_link']})"
    )

    await message.answer_photo(photo=deal['thumb'], caption=text, parse_mode="Markdown")