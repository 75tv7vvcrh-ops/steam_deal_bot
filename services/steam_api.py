import aiohttp
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_top_steam_deals(min_discount: int = 10, max_pages: int = 3):
    url = "https://www.cheapshark.com/api/1.0/deals"
    deals = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    async with aiohttp.ClientSession(headers=headers) as session:
        for page in range(max_pages):
            params = {
                "storeID": "1",
                "sortBy": "Deal Rating",
                "onSale": "1",
                "pageSize": "60",
                "pageNumber": str(page)
            }

            try:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status != 200:
                        break
                    data = await response.json()
                    if not data:
                        break

                    for item in data:
                        try:
                            discount = int(float(item.get('savings', 0)))
                            if discount >= min_discount:
                                thumb = item.get('thumb', '')
                                if thumb and not thumb.startswith('http'):
                                    thumb = f"https://{thumb}"

                                deals.append({
                                    "deal_id": item.get('dealID'),
                                    "title": item.get('title', 'Без названия'),
                                    "normal_price": item.get('normalPrice', '0.00'),
                                    "sale_price": item.get('salePrice', '0.00'),
                                    "discount": discount,
                                    "thumb": thumb,
                                    "steam_app_id": item.get('steamAppID'),
                                    "deal_link": f"https://www.cheapshark.com/redirect?dealID={item.get('dealID')}"
                                })
                        except Exception as e:
                            logger.error(f"Ошибка обработки: {e}")
                            continue
            except Exception as e:
                logger.error(f"Ошибка запроса страницы {page}: {e}")
                break

    return deals

async def search_deals_by_title(title: str, limit: int = 10):
    url = "https://www.cheapshark.com/api/1.0/deals"
    params = {"storeID": "1", "title": title, "pageSize": str(limit)}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status != 200:
                    return []
                data = await response.json()
                deals = []
                for item in data:
                    thumb = item.get('thumb', '')
                    if thumb and not thumb.startswith('http'):
                        thumb = f"https://{thumb}"
                    deals.append({
                        "deal_id": item.get('dealID'),
                        "title": item.get('title', 'Без названия'),
                        "normal_price": item.get('normalPrice', '0.00'),
                        "sale_price": item.get('salePrice', '0.00'),
                        "discount": int(float(item.get('savings', 0))),
                        "thumb": thumb,
                        "steam_app_id": item.get('steamAppID'),
                        "deal_link": f"https://www.cheapshark.com/redirect?dealID={item.get('dealID')}"
                    })
                return deals
        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            return []
