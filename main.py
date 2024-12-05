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

async def check_ffmpeg():
    """檢查 FFMPEG 是否可用"""
    try:
        import subprocess
        process = await asyncio.create_subprocess_exec(
            'ffmpeg', '-version',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            logger.info("FFMPEG 檢查成功：已正確安裝")
            return True
        else:
            logger.error(f"FFMPEG 檢查失敗: {stderr.decode()}")
            return False
    except Exception as e:
        logger.error(f"FFMPEG 檢查失敗: {str(e)}")
        return False

class PartyBot(commands.Bot):
    async def setup_hook(self):
        """在機器人啟動前的初始化設置"""
        try:
            # 檢查 FFMPEG
            if not await check_ffmpeg():
                logger.error("FFMPEG 未正確安裝，音樂功能可能無法使用")
            
            # 載入所有 cog
            cog_list = [
                'music_cog',
                'emoji_cog',
                'utility_cog',
                'utils_cog'
            ]
            
            loaded_commands = set()  # 用於追蹤已載入的命令
            
            for cog in cog_list:
                try:
                    await self.load_extension(cog)
                    logger.info(f"已載入擴展: {cog}")
                except commands.errors.ExtensionFailed as e:
                    if "CommandAlreadyRegistered" in str(e):
                        logger.warning(f"擴展 {cog} 中的某些命令已經註冊")
                        continue
                    logger.error(f"載入擴展 {cog} 時發生錯誤: {str(e)}", exc_info=True)
                except Exception as e:
                    logger.error(f"載入擴展 {cog} 時發生錯誤: {str(e)}", exc_info=True)

            # 同步指令
            logger.info("正在同步指令...")
            synced_commands = await self.tree.sync()
            logger.info(f"成功同步 {len(synced_commands)} 個指令！")
            
            # 移除重複的命令
            unique_commands = {}
            for cmd in self.tree.get_commands():
                if cmd.name not in unique_commands:
                    unique_commands[cmd.name] = cmd
            
            logger.info("\n已註冊的指令：")
            for cmd in unique_commands.values():
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
