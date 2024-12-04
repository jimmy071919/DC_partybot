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

# 根據操作系統設定 FFMPEG 路徑
if platform.system() == 'Windows':
    FFMPEG_PATH = "C:\\Program Files\\ffmpeg-7.1-full_build\\bin\\ffmpeg.exe"
else:
    # Linux 環境（如 Railway）使用系統級 FFMPEG
    FFMPEG_PATH = "ffmpeg"

# 檔案路徑
EMOJI_DATA_PATH = "emoji_data.json"
PLAYLIST_DATA_PATH = "playlists.json"
REMINDERS_DATA_PATH = "reminders.json"
