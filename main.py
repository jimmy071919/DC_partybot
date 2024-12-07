import discord
from discord.ext import commands
import asyncio
import os
from config import DISCORD_TOKEN
import yt_dlp
import logging

# 初始化 Discord bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# 配置更穩定的 YouTube 下載選項
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # 繫結到 IPv4 since IPv6 addresses cause issues sometimes
}

def get_youtube_info(url):
    try:
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        logging.error(f"YouTube 資訊提取錯誤：{e}")
        return None

# 載入所有 cogs
async def load_extensions():
    print("\n正在載入模組...")
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"✓ 已載入: cogs.{filename[:-3]}")
            except Exception as e:
                print(f"✗ 載入失敗 {filename}: {str(e)}")

@bot.event
async def on_ready():
    try:
        print(f"\n正在同步指令...")
        await bot.tree.sync()
        
        # 列出所有已註冊的指令
        print("\n已註冊的指令：")
        print("=" * 50)
        
        # 獲取所有斜線指令
        all_commands = bot.tree.get_commands()
        
        # 按類別分類指令
        command_categories = {}
        for cmd in all_commands:
            # 從指令的完整名稱中提取類別
            category = getattr(cmd.callback, "__cog_name__", "其他")
            if category not in command_categories:
                command_categories[category] = []
            command_categories[category].append(cmd)
        
        # 顯示分類後的指令
        for category, commands in command_categories.items():
            print(f"\n【{category}】")
            for cmd in commands:
                print(f"/{cmd.name}: {cmd.description}")
        
        print("\n" + "=" * 50)
        print(f"✓ 成功同步 {len(all_commands)} 個指令！")
        print(f"✓ Bot 已登入為 {bot.user}")
        print("=" * 50)
        
    except Exception as e:
        print(f"✗ 同步指令時發生錯誤：{str(e)}")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
