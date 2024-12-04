import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from datetime import datetime, timedelta
import json
import os

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reminders = {}
        self.load_reminders()

    def load_reminders(self):
        if os.path.exists('reminders.json'):
            with open('reminders.json', 'r', encoding='utf-8') as f:
                self.reminders = json.load(f)

    def save_reminders(self):
        with open('reminders.json', 'w', encoding='utf-8') as f:
            json.dump(self.reminders, f, ensure_ascii=False, indent=4)

    @app_commands.command(name="random_pick", description="從語音頻道隨機抽取一個成員")
    async def random_pick(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            await interaction.response.send_message("你必須先加入一個語音頻道！", ephemeral=True)
            return
        
        voice_channel = interaction.user.voice.channel
        members = voice_channel.members
        
        if len(members) < 2:
            await interaction.response.send_message("語音頻道中至少需要2個人才能抽籤！", ephemeral=True)
            return
        
        chosen = random.choice(members)
        embed = discord.Embed(
            title="🎲 隨機抽籤結果",
            description=f"恭喜 {chosen.mention} 被選中了！",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="roll", description="擲骰子")
    async def roll(self, interaction: discord.Interaction, max_number: int = 100):
        result = random.randint(1, max_number)
        await interaction.response.send_message(f"🎲 擲出了 {result} 點！")

    @app_commands.command(name="poll", description="建立投票")
    async def poll(self, interaction: discord.Interaction, question: str, options: str):
        options_list = [opt.strip() for opt in options.split(',')]
        
        if len(options_list) < 2 or len(options_list) > 10:
            await interaction.response.send_message("選項數量必須在2到10之間！", ephemeral=True)
            return
        
        # 數字表情符號
        number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        # 建立投票訊息
        embed = discord.Embed(
            title=f"📊 {question}",
            color=discord.Color.blue()
        )
        
        # 加入選項
        for i, option in enumerate(options_list):
            embed.add_field(
                name=f"{number_emojis[i]} {option}",
                value="\u200b",
                inline=False
            )
        
        # 發送投票訊息
        message = await interaction.channel.send(embed=embed)
        await interaction.response.send_message("投票已建立！", ephemeral=True)
        
        # 新增表情反應
        for i in range(len(options_list)):
            await message.add_reaction(number_emojis[i])

    @app_commands.command(name="clear", description="清除訊息")
    @commands.has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: int = 5):
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"已清除 {len(deleted)} 則訊息！", ephemeral=True)

    @app_commands.command(name="userinfo", description="顯示用戶資訊")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        
        embed = discord.Embed(
            title=f"{member.name}的用戶資訊",
            color=member.color
        )
        
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(name="用戶ID", value=member.id)
        embed.add_field(name="暱稱", value=member.nick or "無")
        embed.add_field(name="加入時間", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S"))
        embed.add_field(name="帳號建立時間", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"))
        
        roles = [role.mention for role in member.roles[1:]]  # 排除@everyone
        embed.add_field(name=f"身分組 [{len(roles)}]", value=" ".join(roles) if roles else "無", inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="remind", description="設定提醒")
    async def set_reminder(self, interaction: discord.Interaction, minutes: int, message: str):
        if minutes <= 0:
            await interaction.response.send_message("提醒時間必須大於0分鐘！", ephemeral=True)
            return
        
        remind_time = datetime.now() + timedelta(minutes=minutes)
        reminder_id = str(len(self.reminders) + 1)
        
        self.reminders[reminder_id] = {
            "user_id": interaction.user.id,
            "channel_id": interaction.channel_id,
            "message": message,
            "time": remind_time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.save_reminders()
        
        embed = discord.Embed(
            title="⏰ 提醒已設定",
            description=f"將在 {minutes} 分鐘後提醒你：\n{message}",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)
        
        # 設定提醒
        await asyncio.sleep(minutes * 60)
        
        # 檢查提醒是否仍然存在（可能已被取消）
        if reminder_id in self.reminders:
            channel = self.bot.get_channel(interaction.channel_id)
            user = self.bot.get_user(interaction.user.id)
            
            if channel and user:
                remind_embed = discord.Embed(
                    title="⏰ 提醒時間到！",
                    description=f"{user.mention}\n{message}",
                    color=discord.Color.gold()
                )
                await channel.send(embed=remind_embed)
                
                # 移除已完成的提醒
                del self.reminders[reminder_id]
                self.save_reminders()

async def setup(bot):
    await bot.add_cog(Utility(bot))
