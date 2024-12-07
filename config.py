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

# 檔案路徑
def find_ffmpeg():
    # 嘗試在 Nix store 中找到 ffmpeg
    nix_paths = [
        "/nix/store/*/bin/ffmpeg",
        "/run/current-system/sw/bin/ffmpeg"
    ]
    
    for path_pattern in nix_paths:
        import glob
        matches = glob.glob(path_pattern)
        if matches:
            return matches[0]
    
    # 如果在 Nix store 中找不到，使用 which 命令
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        return ffmpeg_path
    
    # Windows 備用路徑
    if os.name == "nt":
        return "C:\\Program Files\\ffmpeg-7.1-full_build\\bin\\ffmpeg.exe"
    
    return None

FFMPEG_PATH = find_ffmpeg()
if not FFMPEG_PATH:
    raise Exception("找不到 ffmpeg，請確保已正確安裝")

EMOJI_DATA_PATH = os.getenv('EMOJI_DATA_PATH', 'emoji_data.json')
PLAYLIST_DATA_PATH = os.getenv('PLAYLIST_DATA_PATH', 'playlists.json')
REMINDERS_DATA_PATH = os.getenv('REMINDERS_DATA_PATH', 'reminders.json')
