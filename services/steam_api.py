import logging
import asyncio
import aiohttp

logger = logging.getLogger(__name__)

API_URL = "https://www.cheapshark.com/api/1.0/deals"

HEADERS = {
"User-Agent": "SteamDealBot/1.0",
}

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)

def normalize_thumbnail(thumb: str) -> str:
"""Приводит ссылку на изображение к полному URL."""
if thumb and not thumb.startswith("http"):
return f"https://{thumb}"

```
return thumb
```

def format_deal(item: dict) -> dict:
"""Приводит ответ CheapShark к единому формату."""
discount = int(float(item.get("savings", 0)))
deal_id = item.get("dealID")

```
return {
    "deal_id": deal_id,
    "title": item.get("title", "Без названия"),
    "normal_price": item.get("normalPrice", "0.00"),
    "sale_price": item.get("salePrice", "0.00"),
    "discount": discount,
    "thumb": normalize_thumbnail(item.get("thumb", "")),
    "steam_app_id": item.get("steamAppID"),
    "deal_link": (
        f"https://www.cheapshark.com/redirect?dealID={deal_id}"
    ),
}
```

async def get_top_steam_deals(
min_discount: int = 10,
max_pages: int = 3,
):
"""Получает лучшие скидки Steam с CheapShark."""
deals = []

```
async with aiohttp.ClientSession(
    headers=HEADERS,
    timeout=REQUEST_TIMEOUT,
) as session:

    for page in range(max_pages):
        params = {
            "storeID": "1",
            "sortBy": "Deal Rating",
            "onSale": "1",
            "pageSize": "60",
            "pageNumber": str(page),
        }

        try:
            async with session.get(API_URL, params=params) as response:
                if response.status != 200:
                    logger.error(
                        "CheapShark вернул HTTP %s для страницы %s",
                        response.status,
                        page,
                    )
                    break

                data = await response.json()

                if not data:
                    break

                for item in data:
                    try:
                        deal = format_deal(item)

                        if deal["discount"] >= min_discount:
                            deals.append(deal)

                    except (TypeError, ValueError, KeyError) as e:
                        logger.error(
                            "Ошибка обработки сделки: %s",
                            e,
                        )

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error(
                "Ошибка запроса страницы %s: %s",
                page,
                e,
            )
            break

return deals
```

async def search_deals_by_title(
title: str,
limit: int = 10,
):
"""Ищет скидки Steam по названию игры."""
params = {
"storeID": "1",
"title": title,
"pageSize": str(limit),
}

```
async with aiohttp.ClientSession(
    headers=HEADERS,
    timeout=REQUEST_TIMEOUT,
) as session:

    try:
        async with session.get(API_URL, params=params) as response:
            if response.status != 200:
                logger.error(
                    "CheapShark вернул HTTP %s при поиске '%s'",
                    response.status,
                    title,
                )
                return []

            data = await response.json()

            return [
                format_deal(item)
                for item in data
            ]

    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.error(
            "Ошибка поиска '%s': %s",
            title,
            e,
        )
        return []
```
