import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# Discord Bot 設定
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# API Keys
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
TENOR_API_KEY = os.getenv('TENOR_API_KEY')
TENOR_API_URL = os.getenv('TENOR_API_URL')

# 檔案路徑
FFMPEG_PATH = "ffmpeg" if os.name != "nt" else "C:\\Program Files\\ffmpeg-7.1-full_build\\bin\\ffmpeg.exe"
EMOJI_DATA_PATH = os.getenv('EMOJI_DATA_PATH', 'emoji_data.json')
PLAYLIST_DATA_PATH = os.getenv('PLAYLIST_DATA_PATH', 'playlists.json')
REMINDERS_DATA_PATH = os.getenv('REMINDERS_DATA_PATH', 'reminders.json')
