import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import requests
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 設定 Tenor API
TENOR_API_URL = os.getenv('TENOR_API_URL')
TENOR_API_KEY = os.getenv('TENOR_API_KEY')
EMOJI_DATA_PATH = os.getenv('EMOJI_DATA_PATH')

class Emoji(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tree = bot.tree

    def load_emoji_data(self):
        try:
            with open(EMOJI_DATA_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"keywords": {}, "gif_categories": {}}

    async def get_random_gif(self, category):
        params = {
            "q": category,
            "key": TENOR_API_KEY,
            "client_key": "discord_bot",
            "limit": 10,
            "media_filter": "gif"
        }
        
        try:
            response = requests.get(TENOR_API_URL, params=params)
            data = response.json()
            if "results" in data and data["results"]:
                gif = random.choice(data["results"])
                return gif["media_formats"]["gif"]["url"]
        except Exception as e:
            print(f"獲取 GIF 時發生錯誤：{e}")
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
        emojis = self.get_recommended_emojis(text)
        
        if not emojis:
            await interaction.response.send_message("找不到相關的表情符號推薦 😅", ephemeral=True)
            return
        
        await interaction.response.send_message(
            f"推薦的表情符號：{''.join(emojis)}",
            ephemeral=True
        )

    @app_commands.command(name="party_gif", description="獲取隨機派對相關 GIF")
    async def party_gif(self, interaction: discord.Interaction, category: str = "party"):
        emoji_data = self.load_emoji_data()
        
        if category not in emoji_data["gif_categories"]:
            categories = ", ".join(emoji_data["gif_categories"].keys())
            await interaction.response.send_message(
                f"無效的類別！可用類別：{categories}",
                ephemeral=True
            )
            return
        
        search_term = random.choice(emoji_data["gif_categories"][category])
        await interaction.response.defer()
        
        gif_url = await self.get_random_gif(search_term)
        
        if gif_url:
            await interaction.followup.send(gif_url)
        else:
            await interaction.followup.send("抱歉，無法獲取 GIF 😅", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        
        emojis = self.get_recommended_emojis(message.content)
        if emojis and random.random() < 0.3:  # 30% 機率回應
            await message.add_reaction(random.choice(emojis))

async def setup(bot):
    await bot.add_cog(Emoji(bot))
