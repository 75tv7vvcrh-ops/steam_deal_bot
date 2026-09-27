import random
from aiogram import Router, F
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, 
    ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto, LabeledPrice, PreCheckoutQuery
)

from services.steam_api import get_top_steam_deals, search_deals_by_title
from database.db import (
    get_chat_settings, update_chat_settings, 
    add_to_wishlist, remove_from_wishlist, get_wishlist, is_in_wishlist
)

router = Router()
router.message.filter(F.chat.type == "private")

# Временное хранилище списков игр для каждого пользователя в памяти
USER_DEALS_CACHE = {}


# =====================================================================
# КЛАВИАТУРЫ
# =====================================================================

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔥 Горячие скидки"), KeyboardButton(text="🎲 Случайная скидка")],
            [KeyboardButton(text="❤️ Избранное"), KeyboardButton(text="⚙️ Настройки")],
            [KeyboardButton(text="💖 Поддержать")]
        ],
        resize_keyboard=True
    )


async def build_deal_card(user_id: int, deals: list, index: int = 0, mode: str = "general"):
    deal = deals[index]
    total = len(deals)
    
    text = (
        f"🎮 **{deal['title']}**\n\n"
        f"💳 Старая цена: ~${deal['normal_price']}~\n"
        f"🔥 **Скидка:** {deal['discount']}%\n"
        f"✅ **Новая цена:** ${deal['sale_price']}\n\n"
        f"📌 *Игра {index + 1} из {total}*"
    )
    
    in_fav = await is_in_wishlist(user_id, deal['deal_id'])
    fav_text = "💔 Из Избранного" if in_fav else "❤️ В Избранное"
    fav_action = f"fav_toggle:{index}:{mode}"
    
    buttons = [
        [InlineKeyboardButton(text="🛒 Купить в Steam", url=deal['deal_link'])],
        [InlineKeyboardButton(text=fav_text, callback_data=fav_action)]
    ]
    
    nav_buttons = []
    if index > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"page:{mode}:{index - 1}"))
    if index < total - 1:
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"page:{mode}:{index + 1}"))
        
    if nav_buttons:
        buttons.append(nav_buttons)
        
    return deal['thumb'], text, InlineKeyboardMarkup(inline_keyboard=buttons)


def build_settings_keyboard(current_discount: int, current_time: str, current_sort: str):
    discounts = [30, 50, 70, 80]
    times = ["09:00", "12:00", "18:00", "21:00"]
    
    buttons = []
    
    discount_row = [
        InlineKeyboardButton(
            text=f"✅ {d}%" if d == current_discount else f"{d}%", 
            callback_data=f"set_discount:{d}"
        ) for d in discounts
    ]
    
    btn_max = f"✅ 🔥 Макс. рейтинг" if current_sort == "max_rating" else "🔥 Макс. рейтинг"
    btn_min = f"✅ 📉 Мин. рейтинг" if current_sort == "min_rating" else "📉 Мин. рейтинг"
    sort_row = [
        InlineKeyboardButton(text=btn_max, callback_data="set_sort:max_rating"),
        InlineKeyboardButton(text=btn_min, callback_data="set_sort:min_rating")
    ]
    
    time_row = [
        InlineKeyboardButton(
            text=f"✅ {t}" if t == current_time else f"{t}", 
            callback_data=f"set_time:{t}"
        ) for t in times
    ]
        
    buttons.append([InlineKeyboardButton(text="── 🎯 Мин. скидка ──", callback_data="ignore")])
    buttons.append(discount_row)
    buttons.append([InlineKeyboardButton(text="── 📊 Порядок рейтинга ──", callback_data="ignore")])
    buttons.append(sort_row)
    buttons.append([InlineKeyboardButton(text="── ⏰ Время дайджеста ──", callback_data="ignore")])
    buttons.append(time_row)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# =====================================================================
# ОБРАБОТЧИКИ КОМАНД
# =====================================================================

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я **Steam Sales Bot** 🎮\n\n"
        "Я ищу лучшие скидки на игры в Steam.\n\n"
        "🔍 **Как искать игры?**\n"
        "Напиши в чат `/search Название` (например: `/search Cyberpunk`)\n\n"
        "Используй меню ниже для навигации:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )


@router.message(Command("deals"))
@router.message(F.text == "🔥 Горячие скидки")
async def show_deals(message: Message):
    await message.answer("🔍 Ищу актуальные скидки...")
    
    settings = await get_chat_settings(message.chat.id)
    # Принудительно устанавливаем min_discount=0, чтобы гарантированно получать список
    deals = await get_top_steam_deals(min_discount=0, max_pages=3)
    
    if not deals:
        await message.answer("К сожалению, скидок не найдено.")
        return

    if settings["sort_by"] == "min_rating":
        deals.reverse()

    USER_DEALS_CACHE[message.from_user.id] = deals
    image_url, text, keyboard = await build_deal_card(message.from_user.id, deals, index=0, mode="general")
    await message.answer_photo(photo=image_url, caption=text, reply_markup=keyboard, parse_mode="Markdown")


@router.message(F.text == "🎲 Случайная скидка")
async def show_random_deal(message: Message):
    settings = await get_chat_settings(message.chat.id)
    deals = await get_top_steam_deals(min_discount=0, max_pages=3)
    
    if not deals:
        await message.answer("Не удалось найти скидки.")
        return

    if settings["sort_by"] == "min_rating":
        deals.reverse()

    USER_DEALS_CACHE[message.from_user.id] = deals
    random_index = random.randint(0, len(deals) - 1)
    image_url, text, keyboard = await build_deal_card(message.from_user.id, deals, index=random_index, mode="general")
    
    await message.answer("🎰 **Ваша случайная скидка:**", parse_mode="Markdown")
    await message.answer_photo(photo=image_url, caption=text, reply_markup=keyboard, parse_mode="Markdown")


@router.message(Command("search"))
async def cmd_search(message: Message, command: CommandObject):
    if not command.args:
        await message.answer("Пожалуйста, укажите название игры.\nПример: `/search Witcher`", parse_mode="Markdown")
        return

    query = command.args
    await message.answer(f"🔍 Ищу скидки по запросу **«{query}»**...", parse_mode="Markdown")
    
    deals = await search_deals_by_title(query)
    
    if not deals:
        await message.answer(f"По запросу «{query}» ничего не найдено.")
        return

    USER_DEALS_CACHE[message.from_user.id] = deals
    image_url, text, keyboard = await build_deal_card(message.from_user.id, deals, index=0, mode="search")
    await message.answer_photo(photo=image_url, caption=text, reply_markup=keyboard, parse_mode="Markdown")


@router.message(F.text == "❤️ Избранное")
async def show_wishlist(message: Message):
    wishlist = await get_wishlist(message.from_user.id)
    
    if not wishlist:
        await message.answer(
            "💔 **Ваш список избранного пуст.**\n\n"
            "Добавляйте интересные игры нажатием кнопки «❤️ В Избранное» под карточкой игры!",
            parse_mode="Markdown"
        )
        return

    USER_DEALS_CACHE[message.from_user.id] = wishlist
    image_url, text, keyboard = await build_deal_card(message.from_user.id, wishlist, index=0, mode="wishlist")
    await message.answer_photo(photo=image_url, caption=text, reply_markup=keyboard, parse_mode="Markdown")


# =====================================================================
# CALLBACKS
# =====================================================================

@router.callback_query(lambda c: c.data and c.data.startswith("page:"))
async def process_page(callback: CallbackQuery):
    _, mode, index_str = callback.data.split(":")
    target_index = int(index_str)
    user_id = callback.from_user.id
    
    deals = USER_DEALS_CACHE.get(user_id, [])
    if not deals or target_index >= len(deals):
        await callback.answer("Сессия устарела или список пуст. Вызовите /deals заново.", show_alert=True)
        return

    image_url, text, keyboard = await build_deal_card(user_id, deals, index=target_index, mode=mode)
    await callback.message.edit_media(
        media=InputMediaPhoto(media=image_url, caption=text, parse_mode="Markdown"),
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("fav_toggle:"))
async def process_fav_toggle(callback: CallbackQuery):
    _, index_str, mode = callback.data.split(":")
    index = int(index_str)
    user_id = callback.from_user.id
    
    deals = USER_DEALS_CACHE.get(user_id, [])
    if not deals or index >= len(deals):
        await callback.answer("Ошибка данных.", show_alert=True)
        return

    deal = deals[index]
    deal_id = deal['deal_id']
    
    is_fav = await is_in_wishlist(user_id, deal_id)
    if is_fav:
        await remove_from_wishlist(user_id, deal_id)
        await callback.answer("💔 Удалено из Избранного")
    else:
        await add_to_wishlist(user_id, deal)
        await callback.answer("❤️ Добавлено в Избранное!")

    if mode == "wishlist":
        deals = await get_wishlist(user_id)
        USER_DEALS_CACHE[user_id] = deals
        if not deals:
            await callback.message.delete()
            await callback.message.answer("💔 Ваш список Избранного теперь пуст.")
            return
        index = min(index, len(deals) - 1)

    image_url, text, keyboard = await build_deal_card(user_id, deals, index=index, mode=mode)
    await callback.message.edit_reply_markup(reply_markup=keyboard)


# НАСТРОЙКИ
@router.message(Command("settings"))
@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message):
    settings = await get_chat_settings(message.chat.id)
    keyboard = build_settings_keyboard(settings["min_discount"], settings["notify_time"], settings["sort_by"])
    sort_title = "🔥 Макс. рейтинг" if settings["sort_by"] == "max_rating" else "📉 Мин. рейтинг"
    
    await message.answer(
        f"⚙️ **Настройки рассылки**\n\n"
        f"🔥 Мин. скидка: **от {settings['min_discount']}%**\n"
        f"📊 Порядок рейтинга: **{sort_title}**\n"
        f"⏰ Время уведомлений: **{settings['notify_time']}**\n\n"
        f"Настройте параметры ниже:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.callback_query(lambda c: c.data and c.data.startswith("set_discount:"))
async def process_set_discount(callback: CallbackQuery):
    new_discount = int(callback.data.split(":")[1])
    chat_id = callback.message.chat.id
    await update_chat_settings(chat_id, min_discount=new_discount)
    settings = await get_chat_settings(chat_id)
    
    keyboard = build_settings_keyboard(settings["min_discount"], settings["notify_time"], settings["sort_by"])
    sort_title = "🔥 Макс. рейтинг" if settings["sort_by"] == "max_rating" else "📉 Мин. рейтинг"
    
    try:
        await callback.message.edit_text(
            f"⚙️ **Настройки рассылки**\n\n"
            f"🔥 Мин. скидка: **от {settings['min_discount']}%**\n"
            f"📊 Порядок рейтинга: **{sort_title}**\n"
            f"⏰ Время уведомлений: **{settings['notify_time']}**\n\n"
            f"Настройте параметры ниже:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception:
        pass
    await callback.answer(f"Порог скидок: {new_discount}%")


@router.callback_query(lambda c: c.data and c.data.startswith("set_sort:"))
async def process_set_sort(callback: CallbackQuery):
    new_sort = callback.data.split(":")[1]
    chat_id = callback.message.chat.id
    await update_chat_settings(chat_id, sort_by=new_sort)
    settings = await get_chat_settings(chat_id)
    
    keyboard = build_settings_keyboard(settings["min_discount"], settings["notify_time"], settings["sort_by"])
    sort_title = "🔥 Макс. рейтинг" if settings["sort_by"] == "max_rating" else "📉 Мин. рейтинг"
    
    try:
        await callback.message.edit_text(
            f"⚙️ **Настройки рассылки**\n\n"
            f"🔥 Мин. скидка: **от {settings['min_discount']}%**\n"
            f"📊 Порядок рейтинга: **{sort_title}**\n"
            f"⏰ Время уведомлений: **{settings['notify_time']}**\n\n"
            f"Настройте параметры ниже:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception:
        pass
    title = "Макс. рейтинг" if new_sort == "max_rating" else "Мин. рейтинг"
    await callback.answer(f"Порядок изменен на: {title}")


@router.callback_query(lambda c: c.data and c.data.startswith("set_time:"))
async def process_set_time(callback: CallbackQuery):
    new_time = callback.data.split(":")[1]
    chat_id = callback.message.chat.id
    await update_chat_settings(chat_id, notify_time=new_time)
    settings = await get_chat_settings(chat_id)
    
    keyboard = build_settings_keyboard(settings["min_discount"], settings["notify_time"], settings["sort_by"])
    sort_title = "🔥 Макс. рейтинг" if settings["sort_by"] == "max_rating" else "📉 Мин. рейтинг"
    
    try:
        await callback.message.edit_text(
            f"⚙️ **Настройки рассылки**\n\n"
            f"🔥 Мин. скидка: **от {settings['min_discount']}%**\n"
            f"📊 Порядок рейтинга: **{sort_title}**\n"
            f"⏰ Время уведомлений: **{settings['notify_time']}**\n\n"
            f"Настройте параметры ниже:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception:
        pass
    await callback.answer(f"Время рассылки: {new_time}")


@router.callback_query(lambda c: c.data == "ignore")
async def process_ignore(callback: CallbackQuery):
    await callback.answer()


# ДОНАТЫ
@router.message(Command("donate"))
@router.message(F.text == "💖 Поддержать")
async def show_donate(message: Message):
    buttons = [
        [
            InlineKeyboardButton(text="⭐ 50 Stars", callback_data="buy_stars:50"),
            InlineKeyboardButton(text="⭐ 100 Stars", callback_data="buy_stars:100"),
        ],
        [
            InlineKeyboardButton(text="⭐ 250 Stars", callback_data="buy_stars:250"),
            InlineKeyboardButton(text="⭐ 500 Stars", callback_data="buy_stars:500"),
        ]
    ]
    await message.answer(
        "💖 **Поддержка проекта**\n\n"
        "Бот абсолютно бесплатен!\n"
        "Если тебе нравится сервис, ты можешь поддержать его Telegram Звёздами:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown"
    )


@router.callback_query(lambda c: c.data and c.data.startswith("buy_stars:"))
async def process_buy_stars(callback: CallbackQuery):
    amount = int(callback.data.split(":")[1])
    await callback.message.answer_invoice(
        title="Поддержка Steam Sales Bot",
        description=f"Донат {amount} Telegram Stars на развитие бота.",
        payload=f"donate_{amount}_stars",
        currency="XTR",
        prices=[LabeledPrice(label="Донат", amount=amount)]
    )
    await callback.answer()


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(lambda m: m.successful_payment is not None)
async def process_successful_payment(message: Message):
    stars = message.successful_payment.total_amount
    await message.answer(f"🎉 **Спасибо!** Донат в {stars} ⭐ получен!", parse_mode="Markdown")
