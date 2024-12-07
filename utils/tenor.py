import requests
from config import TENOR_API_KEY, TENOR_API_URL

def get_random_gif(category):
    params = {
        "q": category,
        "key": TENOR_API_KEY,
        "client_key": "discord_bot",
        "limit": 10,
        "media_filter": "minimal"
    }
    
    try:
        response = requests.get(TENOR_API_URL, params=params)
        data = response.json()
        
        if "results" in data and data["results"]:
            results = data["results"]
            import random
            result = random.choice(results)
            return result["media_formats"]["gif"]["url"]
    except Exception as e:
        print(f"獲取 GIF 時發生錯誤：{e}")
    
    return None
