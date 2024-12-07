import os
import shutil
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# Discord Bot 設定
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# API Keys
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
TENOR_API_KEY = os.getenv('TENOR_API_KEY')
TENOR_API_URL = os.getenv('TENOR_API_URL')

def find_ffmpeg():
    try:
        # 嘗試找到 FFmpeg
        ffmpeg_path = shutil.which('ffmpeg')
        if ffmpeg_path:
            print(f"找到 FFmpeg：{ffmpeg_path}")
            return ffmpeg_path
        
        # 如果找不到，印出警告但不中斷
        print("警告：找不到 FFmpeg，部分功能可能受限")
        return None
    except Exception as e:
        print(f"檢查 FFmpeg 時發生錯誤：{e}")
        return None

# 嘗試找到 FFmpeg，但不強制要求
FFMPEG_PATH = find_ffmpeg()

EMOJI_DATA_PATH = os.getenv('EMOJI_DATA_PATH', 'emoji_data.json')
PLAYLIST_DATA_PATH = os.getenv('PLAYLIST_DATA_PATH', 'playlists.json')
REMINDERS_DATA_PATH = os.getenv('REMINDERS_DATA_PATH', 'reminders.json')
