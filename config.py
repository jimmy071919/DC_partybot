"""
配置文件 - 處理所有環境變數、檔案路徑和設定
"""
import os
import platform
import shutil
import logging
from pathlib import Path
from dotenv import load_dotenv

# 設置日誌
logger = logging.getLogger(__name__)

# 優先從環境變數載入
ENV_FILES = ['.env', '.ENV']
for env_file in ENV_FILES:
    if Path(env_file).exists():
        load_dotenv(env_file, override=True)
        logger.debug(f"已從 {env_file} 載入環境變數")
        break

# Discord Bot 配置
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', '')
COMMAND_PREFIX = os.getenv('COMMAND_PREFIX', '!')

# YouTube API 配置
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY', '')

# Tenor API 配置
TENOR_API_KEY = os.getenv('TENOR_API_KEY', '')
TENOR_API_URL = os.getenv('TENOR_API_URL', 'https://tenor.googleapis.com/v2/search')

# 獲取 FFMPEG 路徑
def get_ffmpeg_path():
    """根據平台取得 FFMPEG 執行檔路徑"""
    # 如果環境變數中有設置，優先使用
    if os.getenv('FFMPEG_PATH'):
        return os.getenv('FFMPEG_PATH')
        
    # 否則根據作業系統找尋
    if platform.system() == 'Windows':
        # 在 Windows 中嘗試常見的安裝路徑
        common_paths = [
            "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe",
            "C:\\Program Files\\ffmpeg-7.1-full_build\\bin\\ffmpeg.exe",
            "C:\\ffmpeg\\bin\\ffmpeg.exe"
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path
    
    # 使用 which 命令尋找
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        return ffmpeg_path
        
    # 找不到時使用預設名稱 (依賴系統 PATH)
    return 'ffmpeg'

FFMPEG_PATH = get_ffmpeg_path()

# 檔案路徑設定
DATA_DIR = os.getenv('DATA_DIR', 'data')
os.makedirs(DATA_DIR, exist_ok=True)  # 確保資料目錄存在

# 檔案路徑
EMOJI_DATA_PATH = os.path.join(DATA_DIR, os.getenv('EMOJI_DATA_FILE', 'emoji_data.json'))
PLAYLIST_DATA_PATH = os.path.join(DATA_DIR, os.getenv('PLAYLIST_DATA_FILE', 'playlists.json'))
REMINDERS_DATA_PATH = os.path.join(DATA_DIR, os.getenv('REMINDERS_DATA_FILE', 'reminders.json'))

# 檢查必要的 API 密鑰
def validate_config():
    """檢查必要的配置參數是否存在"""
    missing_keys = []
    
    if not DISCORD_TOKEN:
        missing_keys.append("DISCORD_TOKEN")
    
    if not YOUTUBE_API_KEY:
        missing_keys.append("YOUTUBE_API_KEY")
        
    if not TENOR_API_KEY:
        missing_keys.append("TENOR_API_KEY")
        
    if missing_keys:
        logger.warning(f"⚠️ 缺少以下環境變數: {', '.join(missing_keys)}")
        return False
        
    return True
