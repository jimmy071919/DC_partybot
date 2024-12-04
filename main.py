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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('discord_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_token():
    """載入並驗證 Discord Token"""
    load_dotenv(override=True)
    token = os.getenv("DISCORD_TOKEN", "").strip()
    
    if not token:
        logger.error("找不到 DISCORD_TOKEN 環境變數或變數為空")
        return None
        
    if token.startswith('='):
        token = token[1:].strip()
        
    if not (token.startswith('MT') or token.startswith('NT')):
        logger.warning("Discord Token 格式可能不正確")
        logger.warning("一般的 Bot Token 應該以 'MT' 或 'NT' 開頭")
        
    logger.debug(f"Token 長度: {len(token)}, 開頭: {token[:5]}...")
    return token

def load_cogs(bot):
    """載入所有 Cog 擴展"""
    success_count = 0
    cogs = [
        'music_cog',
        'emoji_cog',
        'utility_cog'
    ]
    
    for cog in cogs:
        try:
            asyncio.run(bot.load_extension(cog))
            logger.info(f"已載入擴展: {cog}")
            success_count += 1
        except Exception as e:
            logger.error(f"載入擴展 {cog} 時發生錯誤: {str(e)}", exc_info=True)
    return success_count

async def check_ffmpeg():
    """檢查 FFMPEG 是否可用"""
    try:
        import subprocess
        await asyncio.create_subprocess_exec(
            'ffmpeg', '-version',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        logger.info("FFMPEG 檢查成功：已正確安裝")
        return True
    except Exception as e:
        logger.error(f"FFMPEG 檢查失敗: {str(e)}")
        return False

class PartyBot(commands.Bot):
    async def setup_hook(self):
        """在機器人啟動前的初始化設置"""
        try:
            # 先載入所有 cog
            for filename in os.listdir("./"):
                if filename.endswith("_cog.py"):
                    try:
                        await self.load_extension(filename[:-3])
                        logger.info(f"已載入擴展: {filename[:-3]}")
                    except Exception as e:
                        logger.error(f"載入擴展 {filename[:-3]} 時發生錯誤: {str(e)}", exc_info=True)

            # 然後同步指令
            logger.info("正在同步指令...")
            commands = await self.tree.sync()
            logger.info(f"成功同步 {len(commands)} 個指令！")
            
            logger.info("\n已註冊的指令：")
            for cmd in self.tree.get_commands():
                logger.info(f"- /{cmd.name}: {cmd.description}")
        except Exception as e:
            logger.error(f"同步指令時發生錯誤: {str(e)}", exc_info=True)
        
    async def on_ready(self):
        """機器人啟動完成時的處理"""
        logger.info(f"已登入為 {self.user}")

    async def on_error(self, event, *args, **kwargs):
        """全局錯誤處理"""
        logger.error(f"事件 {event} 發生錯誤", exc_info=True)

async def main():
    """主程式入口"""
    token = load_token()
    if not token:
        return
        
    # 初始化機器人
    intents = discord.Intents.all()
    bot = PartyBot(command_prefix="!", intents=intents)
    
    # 檢查必要組件
    await check_ffmpeg()
    
    try:
        logger.info("正在啟動機器人...")
        await bot.start(token)
    except discord.LoginFailure as e:
        logger.error(f"登入失敗: {str(e)}")
    except Exception as e:
        logger.error(f"發生未預期的錯誤: {str(e)}", exc_info=True)
    finally:
        if not bot.is_closed():
            await bot.close()
            logger.info("機器人正常關閉")

def run_bot():
    """執行機器人"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("收到中斷信號，正在關閉機器人...")
    except Exception as e:
        logger.error(f"執行時發生錯誤: {str(e)}", exc_info=True)

if __name__ == "__main__":
    run_bot()
