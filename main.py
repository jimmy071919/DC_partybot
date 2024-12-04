import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from dotenv import load_dotenv
import os

# 載入環境變數
load_dotenv(override=True)  # 確保重新載入環境變數

# 檢查 token
token = os.getenv("DISCORD_TOKEN")
if not token:
    print("錯誤：找不到 DISCORD_TOKEN 環境變數")
    print("請確保在 Railway 的 Variables 中設置了 DISCORD_TOKEN")
    print("或者在本地開發時在 .env 文件中設置了 DISCORD_TOKEN")
    exit(1)

# 清理 token
token = token.strip()  # 移除空白字符
if token.startswith('='): # 移除開頭的等號
    token = token[1:]
token = token.strip()  # 再次移除可能的空白

if not token:
    print("錯誤：DISCORD_TOKEN 是空的")
    exit(1)

# 驗證 token 格式
if not (token.startswith('MT') or token.startswith('NT')):
    print("警告：Discord Token 格式可能不正確")
    print("一般的 Bot Token 應該以 'MT' 或 'NT' 開頭")
    print("目前的 Token 開頭為：", token[:5] + "...")

print(f"Token 資訊：")
print(f"- 長度: {len(token)}")
print(f"- 開頭字符: {token[:5]}...")
print(f"- 是否包含空格: {' ' in token}")

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
    try:
        await setup()
        print("正在啟動機器人...")
        await bot.start(token)  # 使用之前驗證過的 token 變數
    except discord.LoginFailure as e:
        print(f"登入失敗！請檢查 Discord Token 是否正確")
        print(f"錯誤信息: {str(e)}")
        exit(1)
    except Exception as e:
        print(f"啟動時發生未預期的錯誤：{str(e)}")
        print(f"錯誤類型：{type(e).__name__}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
