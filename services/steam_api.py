import aiohttp
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "SteamDealBot/1.0 (Telegram Steam Deal Bot)"
}

def format_deal(item: dict) -> dict:
    thumb = item.get("thumb", "")
    if thumb and not thumb.startswith("http"):
        thumb = f"https://{thumb}"

    return {
        "deal_id": item.get("dealID"),
        "title": item.get("title", "Без названия"),
        "normal_price": item.get("normalPrice", "0.00"),
        "sale_price": item.get("salePrice", "0.00"),
        "discount": int(float(item.get("savings", 0))),
        "thumb": thumb,
        "steam_app_id": item.get("steamAppID"),
        "deal_link": (
            f"https://www.cheapshark.com/redirect?dealID={item.get('dealID')}"
        ),
    }

async def get_top_steam_deals(min_discount: int = 10, max_pages: int = 3):
    url = "https://www.cheapshark.com/api/1.0/deals"
    deals = []
    

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        for page in range(max_pages):
            params = {
                "storeID": "1",
                "sortBy": "Deal Rating",
                "pageSize": "60",
                "pageNumber": str(page)
            }

            try:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        if response.status != 200:
                        logger.error(
                            "CheapShark вернул HTTP %s для страницы %s",
                            response.status,
                            page
                        )
                        break
                    try:
                        data = await response.json()
                    except (aiohttp.ContentTypeError, ValueError) as e:
                        logger.error("Ошибка чтения ответа CheapShark: %s", e)
                        break
                    if not data:
                        break

                    for item in data:
                        try:
                            deal = format_deal(item)

                            if deal["discount"] >= min_discount:
                                deals.append(deal)
                        except Exception as e:
                            logger.error(f"Ошибка обработки: {e}")
                            continue
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.error(f"Ошибка запроса страницы {page}: {e}")
                break

    return deals

async def search_deals_by_title(title: str, limit: int = 10):
    url = "https://www.cheapshark.com/api/1.0/deals"
    params = {"storeID": "1", "title": title, "pageSize": str(limit)}

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status != 200:
                    logger.error(
                        "CheapShark вернул HTTP %s при поиске '%s'",
                        response.status,
                        title
                    )
                    return []
                try:
                    data = await response.json()
                except (aiohttp.ContentTypeError, ValueError) as e:
                    logger.error("Ошибка чтения ответа CheapShark при поиске '%s': %s", title, e)
                    return []
                deals = []
                for item in data:
                    deals.append(format_deal(item))
                return deals
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error(f"Ошибка поиска: {e}")
            return []
