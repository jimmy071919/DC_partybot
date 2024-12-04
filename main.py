import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from dotenv import load_dotenv
import os
import logging

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('discord_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 載入環境變數
load_dotenv(override=True)

# 檢查 token
token = os.getenv("DISCORD_TOKEN")
if not token:
    logger.error("找不到 DISCORD_TOKEN 環境變數")
    exit(1)

# 清理 token
token = token.strip()
if token.startswith('='):
    token = token[1:]
token = token.strip()

if not token:
    logger.error("DISCORD_TOKEN 是空的")
    exit(1)

# 驗證 token 格式
if not (token.startswith('MT') or token.startswith('NT')):
    logger.warning("Discord Token 格式可能不正確")
    logger.warning("一般的 Bot Token 應該以 'MT' 或 'NT' 開頭")
    logger.warning(f"目前的 Token 開頭為：{token[:5]}...")

logger.info(f"Token 資訊：")
logger.info(f"- 長度: {len(token)}")
logger.info(f"- 開頭字符: {token[:5]}...")
logger.info(f"- 是否包含空格: {' ' in token}")

# 初始化 Discord 機器人
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# 機器人啟動事件
@bot.event
async def on_ready():
    try:
        logger.info(f"登入成功: {bot.user.name}")
        logger.info("正在同步指令...")
        commands = await tree.sync()
        logger.info(f"同步了 {len(commands)} 個指令")
        
        # 列出所有已註冊的指令
        logger.info("\n已註冊的指令：")
        for cmd in tree.get_commands():
            logger.info(f"- /{cmd.name}: {cmd.description}")
            
    except Exception as e:
        logger.error(f"同步指令時發生錯誤: {str(e)}", exc_info=True)

@bot.event
async def on_error(event, *args, **kwargs):
    logger.error(f"事件 {event} 發生錯誤", exc_info=True)

# 設置 Cogs
def setup():
    for filename in os.listdir("./"):
        if filename.endswith("_cog.py"):
            try:
                bot.load_extension(filename[:-3])
                logger.info(f"已載入擴展: {filename[:-3]}")
            except Exception as e:
                logger.error(f"載入擴展 {filename[:-3]} 時發生錯誤: {str(e)}", exc_info=True)

async def main():
    try:
        # 檢查 FFMPEG 是否可用
        import subprocess
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            logger.info("FFMPEG 檢查成功：已正確安裝")
        except subprocess.CalledProcessError:
            logger.warning("FFMPEG 可能未正確安裝")
        except FileNotFoundError:
            logger.error("找不到 FFMPEG，請確保已正確安裝")
            
        setup()
        logger.info("正在啟動機器人...")
        await bot.start(token)  # 使用之前驗證過的 token 變數
    except discord.LoginFailure as e:
        logger.error(f"登入失敗！請檢查 Discord Token 是否正確")
        logger.error(f"錯誤信息: {str(e)}")
        exit(1)
    except Exception as e:
        logger.error(f"運行時發生錯誤: {str(e)}", exc_info=True)
    finally:
        await bot.close()

def run_bot():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("機器人正常關閉")
    except Exception as e:
        logger.error(f"運行時發生嚴重錯誤: {str(e)}", exc_info=True)

if __name__ == "__main__":
    run_bot()
