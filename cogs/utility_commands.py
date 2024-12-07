import discord
from discord.ext import commands
from discord import app_commands
import random
from datetime import datetime, timedelta
from utils.reminders import ReminderSystem
from utils.tenor import get_random_gif

class UtilityCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reminder_system = ReminderSystem()

    @app_commands.command(name="random_pick", description="從語音頻道中隨機選擇一個成員")
    async def random_pick(self, interaction: discord.Interaction):
        if interaction.user.voice and interaction.user.voice.channel:
            members = interaction.user.voice.channel.members
            if members:
                chosen = random.choice(members)
                await interaction.response.send_message(f"🎲 隨機選擇：{chosen.mention}")
            else:
                await interaction.response.send_message("語音頻道中沒有成員！", ephemeral=True)
        else:
            await interaction.response.send_message("你需要先加入一個語音頻道！", ephemeral=True)

    @app_commands.command(name="roll", description="擲骰子")
    async def roll(self, interaction: discord.Interaction, max_number: int = 100):
        result = random.randint(1, max_number)
        await interaction.response.send_message(f"🎲 擲出了 {result} (1-{max_number})")

    @app_commands.command(name="poll", description="建立投票")
    async def poll(self, interaction: discord.Interaction, question: str, options: str):
        options_list = options.split(',')
        if len(options_list) < 2:
            await interaction.response.send_message("請至少提供兩個選項！", ephemeral=True)
            return

        embed = discord.Embed(title="📊 投票", description=question, color=discord.Color.blue())
        
        emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
        
        for i, option in enumerate(options_list[:10]):
            embed.add_field(name=f"{emojis[i]} {option.strip()}", value="", inline=False)

        poll_message = await interaction.response.send_message(embed=embed)
        message = await poll_message.original_message()
        
        for i in range(len(options_list[:10])):
            await message.add_reaction(emojis[i])

    @app_commands.command(name="clear", description="清除訊息")
    async def clear(self, interaction: discord.Interaction, amount: int = 5):
        if amount < 1 or amount > 100:
            await interaction.response.send_message("請指定 1-100 之間的數量！", ephemeral=True)
            return
        
        await interaction.response.defer()
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"🗑️ 已清除 {len(deleted)} 則訊息", ephemeral=True)

    @app_commands.command(name="userinfo", description="顯示用戶資訊")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        
        embed = discord.Embed(title="用戶資訊", color=target.color)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        embed.add_field(name="用戶名稱", value=str(target), inline=True)
        embed.add_field(name="ID", value=target.id, inline=True)
        embed.add_field(name="加入時間", value=target.joined_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="帳號建立時間", value=target.created_at.strftime("%Y-%m-%d"), inline=True)
        
        roles = [role.mention for role in target.roles[1:]]
        embed.add_field(name=f"身分組 [{len(roles)}]", value=" ".join(roles) if roles else "無", inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="remind", description="設定提醒")
    async def remind(self, interaction: discord.Interaction, minutes: int, message: str):
        if minutes < 1:
            await interaction.response.send_message("提醒時間必須大於 1 分鐘！", ephemeral=True)
            return
        
        reminder_time = self.reminder_system.add_reminder(
            str(interaction.user.id),
            str(interaction.channel_id),
            message,
            minutes
        )
        
        await interaction.response.send_message(
            f"⏰ 已設定提醒：\n"
            f"時間：{reminder_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"內容：{message}"
        )

    @app_commands.command(name="gif", description="發送隨機 GIF")
    async def gif(self, interaction: discord.Interaction, category: str = "random"):
        gif_url = get_random_gif(category)
        if gif_url:
            embed = discord.Embed(color=discord.Color.blue())
            embed.set_image(url=gif_url)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ 找不到相關的 GIF", ephemeral=True)

    @app_commands.command(name="help", description="顯示指令說明")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🤖 機器人指令說明", color=discord.Color.blue())
        
        music_commands = """
        `/join` - 讓機器人加入語音頻道
        `/play` - 播放音樂
        `/queue` - 顯示播放佇列
        `/skip` - 跳過當前歌曲
        `/pause` - 暫停播放
        `/resume` - 恢復播放
        `/stop` - 停止播放
        `/leave` - 離開語音頻道
        `/volume` - 調整音量
        `/now_playing` - 顯示當前播放曲目
        """
        embed.add_field(name="🎵 音樂指令", value=music_commands.strip(), inline=False)
        
        utility_commands = """
        `/random_pick` - 隨機選擇成員
        `/roll` - 擲骰子
        `/poll` - 建立投票
        `/clear` - 清除訊息
        `/userinfo` - 顯示用戶資訊
        `/remind` - 設定提醒
        `/gif` - 發送隨機 GIF
        """
        embed.add_field(name="🛠️ 實用指令", value=utility_commands.strip(), inline=False)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(UtilityCommands(bot))
