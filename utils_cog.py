import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import json
from datetime import datetime, timedelta
from config import REMINDERS_DATA_PATH

class Utils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tree = bot.tree
        self.reminders = {}
        self.load_reminders()

    def cog_load(self):
        self.check_reminders.start()

    def cog_unload(self):
        self.check_reminders.cancel()

    def load_reminders(self):
        try:
            with open(REMINDERS_DATA_PATH, 'r', encoding='utf-8') as f:
                self.reminders = json.load(f)
        except FileNotFoundError:
            self.reminders = {}

    def save_reminders(self):
        with open(REMINDERS_DATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.reminders, f, ensure_ascii=False, indent=2)

    @tasks.loop(seconds=60)
    async def check_reminders(self):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        if current_time in self.reminders:
            for reminder in self.reminders[current_time]:
                channel = self.bot.get_channel(reminder["channel_id"])
                if channel:
                    await channel.send(f"<@{reminder['user_id']}> 提醒：{reminder['message']}")
            del self.reminders[current_time]
            self.save_reminders()

    @app_commands.command(name="random", description="從語音頻道中隨機抽選一個人")
    async def random_pick(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            await interaction.response.send_message("你必須先加入語音頻道！", ephemeral=True)
            return
        
        voice_channel = interaction.user.voice.channel
        members = [member for member in voice_channel.members if not member.bot]
        
        if not members:
            await interaction.response.send_message("語音頻道中沒有其他成員！", ephemeral=True)
            return
        
        chosen_one = random.choice(members)
        
        embed = discord.Embed(
            title="🎲 隨機抽選結果",
            description=f"恭喜 **{chosen_one.display_name}** 被選中！",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=chosen_one.display_avatar.url)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="roll", description="擲骰子 (預設 1-100)")
    async def roll(self, interaction: discord.Interaction, max_number: int = 100):
        if max_number < 1:
            await interaction.response.send_message("請輸入大於 0 的數字！", ephemeral=True)
            return
        
        result = random.randint(1, max_number)
        await interaction.response.send_message(f"🎲 {interaction.user.display_name} 擲出了 **{result}** 點！")

    @app_commands.command(name="poll", description="建立投票")
    async def poll(self, interaction: discord.Interaction, question: str, options: str):
        option_list = [opt.strip() for opt in options.split(',')]
        
        if len(option_list) < 2:
            await interaction.response.send_message("至少需要2個選項！", ephemeral=True)
            return
        elif len(option_list) > 20:
            await interaction.response.send_message("最多只能有20個選項！", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=question,
            description="請點擊下方表情符號來投票！",
            color=discord.Color.blue()
        )
        
        for i, option in enumerate(option_list):
            embed.add_field(
                name=f"{i+1}. {option}", 
                value="", 
                inline=False
            )
        
        message = await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()
        
        for i in range(len(option_list)):
            if i < 10:
                await message.add_reaction(f"{i+1}\u20e3")
            else:
                await message.add_reaction(chr(0x1F1E6 + (i-10)))

    @app_commands.command(name="clear", description="清除指定數量的訊息")
    async def clear(self, interaction: discord.Interaction, amount: int = 5):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("你沒有權限執行此指令！", ephemeral=True)
            return
        
        if amount < 1 or amount > 100:
            await interaction.response.send_message("請輸入 1-100 之間的數字！", ephemeral=True)
            return
        
        await interaction.response.defer()
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"已清除 {len(deleted)} 則訊息！", ephemeral=True)

    @app_commands.command(name="userinfo", description="顯示用戶資訊")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        if member is None:
            member = interaction.user
        
        embed = discord.Embed(
            title=f"👤 {member.display_name} 的資訊",
            color=member.color
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="用戶 ID", value=member.id, inline=True)
        embed.add_field(name="加入時間", value=member.joined_at.strftime("%Y/%m/%d"), inline=True)
        embed.add_field(name="帳號建立時間", value=member.created_at.strftime("%Y/%m/%d"), inline=True)
        embed.add_field(name="身分組", value=" ".join([role.mention for role in member.roles[1:]]) or "無", inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="remind", description="設定提醒")
    async def set_reminder(self, interaction: discord.Interaction, minutes: int, message: str):
        if minutes <= 0:
            await interaction.response.send_message("請輸入大於 0 的分鐘數！", ephemeral=True)
            return
        
        remind_time = datetime.now() + timedelta(minutes=minutes)
        time_str = remind_time.strftime("%Y-%m-%d %H:%M")
        
        if time_str not in self.reminders:
            self.reminders[time_str] = []
        
        self.reminders[time_str].append({
            "user_id": interaction.user.id,
            "channel_id": interaction.channel_id,
            "message": message
        })
        
        self.save_reminders()
        
        await interaction.response.send_message(
            f"已設定提醒！\n時間：{time_str}\n內容：{message}",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Utils(bot))
