import aiohttp
import random
from config import TENOR_API_KEY

TENOR_API_URL = "https://tenor.googleapis.com/v2"

async def get_random_gif(search_term):
    try:
        if not TENOR_API_KEY:
            raise ValueError("未設定 TENOR_API_KEY")

        params = {
            "q": search_term,
            "key": TENOR_API_KEY,
            "client_key": "discord_party_bot",
            "limit": 10,
            "media_filter": "gif"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{TENOR_API_URL}/search", params=params) as response:
                if response.status != 200:
                    raise Exception(f"Tenor API 錯誤：{response.status}")
                
                data = await response.json()
                results = data.get("results", [])
                
                if not results:
                    return None
                
                # 隨機選擇一個 GIF
                gif = random.choice(results)
                media_formats = gif.get("media_formats", {})
                
                # 優先使用 gif 格式，如果沒有就用 mediumgif
                url = None
                if "gif" in media_formats:
                    url = media_formats["gif"]["url"]
                elif "mediumgif" in media_formats:
                    url = media_formats["mediumgif"]["url"]
                
                if not url:
                    raise Exception("找不到合適的 GIF 格式")
                
                return url

    except Exception as e:
        print(f"獲取 GIF 時發生錯誤：{str(e)}")
        return None
