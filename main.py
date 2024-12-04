import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from dotenv import load_dotenv
import os

# 載入環境變數
load_dotenv()

# 檢查 token
token = os.getenv("DISCORD_TOKEN")
if not token:
    print("錯誤：找不到 DISCORD_TOKEN 環境變數")
    exit(1)
print("Token 長度：", len(token))  # 不要輸出完整 token，只輸出長度

# 初始化 Discord 機器人
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# 機器人啟動事件
@bot.event
async def on_ready():
    try:
        print(f"正在同步指令...")
        # 強制同步所有指令
        commands = await tree.sync()
        print(f"成功同步 {len(commands)} 個指令！")
        print(f"已登入為 {bot.user}")
        
        # 列出所有已註冊的指令
        print("\n已註冊的指令：")
        for cmd in tree.get_commands():
            print(f"- /{cmd.name}: {cmd.description}")
            
    except Exception as e:
        print(f"同步指令時發生錯誤：{str(e)}")

async def setup():
    # 載入所有 Cogs
    await bot.load_extension('music_cog')
    await bot.load_extension('emoji_cog')
    await bot.load_extension('utils_cog')

async def main():
    await setup()
    await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())
