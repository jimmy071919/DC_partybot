# Discord Bot 配置
DISCORD_TOKEN = ""

# YouTube API 配置
YOUTUBE_API_KEY = ""

# Tenor API 配置
TENOR_API_KEY = ""
TENOR_API_URL = "https://tenor.googleapis.com/v2/search"

# 路徑配置
import platform
import os
import shutil

# 獲取 FFMPEG 路徑
def get_ffmpeg_path():
    if platform.system() == 'Windows':
        return "C:\\Program Files\\ffmpeg-7.1-full_build\\bin\\ffmpeg.exe"
    else:
        # 在 Linux 上尋找 ffmpeg
        ffmpeg_path = shutil.which('ffmpeg')
        if ffmpeg_path:
            return ffmpeg_path
        return 'ffmpeg'  # 如果找不到，使用默認路徑

FFMPEG_PATH = get_ffmpeg_path()

# 檔案路徑
EMOJI_DATA_PATH = "emoji_data.json"
PLAYLIST_DATA_PATH = "playlists.json"
REMINDERS_DATA_PATH = "reminders.json"
