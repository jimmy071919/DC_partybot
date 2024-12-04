import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import os
from dotenv import load_dotenv
import logging
import aiohttp

# 載入環境變數
load_dotenv()

# 設定 Tenor API 和檔案路徑
TENOR_API_URL = os.getenv('TENOR_API_URL', 'https://tenor.googleapis.com/v2/search')
TENOR_API_KEY = os.getenv('TENOR_API_KEY')
EMOJI_DATA_PATH = os.getenv('EMOJI_DATA_PATH', 'emoji_data.json')

class Emoji(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tree = bot.tree
        self.logger = logging.getLogger(__name__)

    def load_emoji_data(self):
        try:
            with open(EMOJI_DATA_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning(f"找不到表情符號數據文件：{EMOJI_DATA_PATH}")
            return {"keywords": {}, "gif_categories": {}}
        except json.JSONDecodeError:
            self.logger.error(f"表情符號數據文件格式錯誤：{EMOJI_DATA_PATH}")
            return {"keywords": {}, "gif_categories": {}}
        except Exception as e:
            self.logger.error(f"載入表情符號數據時發生錯誤：{str(e)}")
            return {"keywords": {}, "gif_categories": {}}

    async def get_random_gif(self, category):
        if not TENOR_API_KEY:
            self.logger.warning("未設定 Tenor API Key")
            return None
            
        params = {
            "q": category,
            "key": TENOR_API_KEY,
            "client_key": "discord_bot",
            "limit": 10,
            "media_filter": "gif"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(TENOR_API_URL, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "results" in data and data["results"]:
                            gif = random.choice(data["results"])
                            return gif["media_formats"]["gif"]["url"]
                    else:
                        self.logger.error(f"Tenor API 返回錯誤：{response.status}")
        except Exception as e:
            self.logger.error(f"獲取 GIF 時發生錯誤：{str(e)}")
        return None

    def get_recommended_emojis(self, text):
        emoji_data = self.load_emoji_data()
        recommended = []
        
        for keyword, emojis in emoji_data["keywords"].items():
            if keyword in text:
                recommended.extend(random.sample(emojis, min(3, len(emojis))))
        
        return list(set(recommended))

    @app_commands.command(name="emoji", description="獲取表情符號推薦")
    async def recommend_emoji(self, interaction: discord.Interaction, text: str):
        """根據文字推薦表情符號"""
        try:
            if not text:
                await interaction.response.send_message("請輸入一些文字來獲取表情符號推薦！", ephemeral=True)
                return

            emojis = self.get_recommended_emojis(text)
            
            if not emojis:
                await interaction.response.send_message(
                    "找不到相關的表情符號推薦 😅\n"
                    "試試輸入：開心、難過、生氣、驚訝、愛心、讚、party 等關鍵字！",
                    ephemeral=True
                )
                return
            
            await interaction.response.send_message(
                f"文字：{text}\n推薦的表情符號：{''.join(emojis)}",
                ephemeral=True
            )
        except Exception as e:
            self.logger.error(f"推薦表情符號時發生錯誤：{str(e)}")
            await interaction.response.send_message("處理請求時發生錯誤，請稍後再試！", ephemeral=True)

    @app_commands.command(name="party_gif", description="獲取隨機派對相關 GIF")
    @app_commands.choices(category=[
        app_commands.Choice(name="派對", value="party"),
        app_commands.Choice(name="開心", value="happy"),
        app_commands.Choice(name="難過", value="sad"),
        app_commands.Choice(name="生氣", value="angry"),
        app_commands.Choice(name="愛心", value="love")
    ])
    async def party_gif(self, interaction: discord.Interaction, category: str = "party"):
        """獲取特定類別的 GIF"""
        try:
            emoji_data = self.load_emoji_data()
            
            if category not in emoji_data["gif_categories"]:
                categories = ", ".join(emoji_data["gif_categories"].keys())
                await interaction.response.send_message(
                    f"無效的類別！可用類別：{categories}",
                    ephemeral=True
                )
                return
            
            await interaction.response.defer()
            
            search_term = random.choice(emoji_data["gif_categories"][category])
            gif_url = await self.get_random_gif(search_term)
            
            if gif_url:
                embed = discord.Embed(color=discord.Color.random())
                embed.set_image(url=gif_url)
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(
                    "抱歉，無法獲取 GIF 😅\n"
                    "可能是 API 限制或網路問題，請稍後再試！",
                    ephemeral=True
                )
        except Exception as e:
            self.logger.error(f"獲取 GIF 時發生錯誤：{str(e)}")
            await interaction.followup.send("處理請求時發生錯誤，請稍後再試！", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        """監聽訊息並自動回應表情符號"""
        if message.author == self.bot.user:
            return
        
        try:
            # 只在一般文字頻道中回應
            if not isinstance(message.channel, discord.TextChannel):
                return
                
            emojis = self.get_recommended_emojis(message.content)
            if emojis and random.random() < 0.9:  # 30% 機率回應
                await message.add_reaction(random.choice(emojis))
        except Exception as e:
            self.logger.error(f"處理訊息表情符號時發生錯誤：{str(e)}")

async def setup(bot):
    """設置 Emoji cog"""
    if not os.path.exists(EMOJI_DATA_PATH):
        # 如果 emoji 數據文件不存在，創建一個基本的
        default_data = {
            "keywords": {
                "開心": ["😊", "😄", "🎉"],
                "難過": ["😢", "😭", "😔"],
                "生氣": ["😠", "😡", "💢"],
                "驚訝": ["😮", "😲", "😱"],
                "愛心": ["❤️", "💕", "💗"],
                "讚": ["👍", "👆", "🆙"],
                "party": ["🎉", "🎊", "🎈"]
            },
            "gif_categories": {
                "party": ["party", "celebration", "dance"],
                "happy": ["happy", "joy", "excited"],
                "sad": ["sad", "crying", "disappointed"],
                "angry": ["angry", "mad", "rage"],
                "love": ["love", "heart", "romantic"]
            }
        }
        with open(EMOJI_DATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, ensure_ascii=False, indent=4)
    
    await bot.add_cog(Emoji(bot))
