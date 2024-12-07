import discord
from discord.ext import commands
from discord import app_commands
import html
from music.queue import MusicQueue, queues
from music.player import play_next
from music.youtube import search_youtube

class SongSelectView(discord.ui.View):
    def __init__(self, videos, bot):
        super().__init__(timeout=30.0)
        self.videos = videos
        self.bot = bot
        
        # 創建 1-10 的按鈕
        for i in range(min(10, len(videos))):
            button = discord.ui.Button(
                label=str(i + 1),
                style=discord.ButtonStyle.primary,
                custom_id=f"select_{i}"
            )
            button.callback = self.create_callback(i)
            self.add_item(button)
    
    def create_callback(self, index):
        async def button_callback(interaction: discord.Interaction):
            selected_video = self.videos[index]
            
            # 確保機器人在語音頻道中
            if not interaction.guild.voice_client:
                if interaction.user.voice:
                    await interaction.user.voice.channel.connect()
                else:
                    await interaction.response.send_message("請先加入語音頻道！", ephemeral=True)
                    return
            
            # 初始化該伺服器的播放佇列
            if interaction.guild_id not in queues:
                queues[interaction.guild_id] = MusicQueue()
            
            queue = queues[interaction.guild_id]
            queue.voice_client = interaction.guild.voice_client
            
            # 將歌曲加入佇列
            queue.add(selected_video)
            
            # 如果沒有在播放，開始播放
            if not queue.is_playing:
                await play_next(interaction.guild_id, self.bot, interaction)
                await interaction.response.send_message(f"🎵 開始播放：{html.unescape(selected_video['title'])}")
            else:
                await interaction.response.send_message(f"➕ 已加入播放佇列：{html.unescape(selected_video['title'])}")
            
            # 禁用所有按鈕
            for child in self.children:
                child.disabled = True
            await interaction.message.edit(view=self)
            
        return button_callback

class MusicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="join", description="讓機器人加入用戶所在的語音頻道")
    async def join(self, interaction: discord.Interaction):
        if interaction.user.voice:
            channel = interaction.user.voice.channel
            try:
                await channel.connect()
                await interaction.response.send_message("已加入語音頻道！")
            except discord.ClientException:
                await interaction.response.send_message("機器人已經在語音頻道內！", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("機器人沒有加入語音頻道的權限！", ephemeral=True)
        else:
            await interaction.response.send_message("你需要先加入一個語音頻道！", ephemeral=True)

    @app_commands.command(name="play", description="播放指定關鍵字的音樂")
    async def play(self, interaction: discord.Interaction, query: str):
        if not interaction.user.voice:
            await interaction.response.send_message("請先加入語音頻道！", ephemeral=True)
            return

        try:
            videos = search_youtube(query)
        except Exception as e:
            print(f"搜尋錯誤：{e}")
            await interaction.response.send_message("搜尋時發生錯誤！", ephemeral=True)
            return

        embed = discord.Embed(title="YouTube 搜尋結果", color=discord.Color.blue())
        for i, video in enumerate(videos):
            embed.add_field(
                name=f"{i+1}. {html.unescape(video['title'])}", 
                value=f"頻道: {video['channel']}\n[點擊觀看]({video['url']})", 
                inline=False
            )

        view = SongSelectView(videos, self.bot)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="skip", description="跳過當前歌曲")
    async def skip(self, interaction: discord.Interaction):
        if interaction.guild_id in queues:
            queue = queues[interaction.guild_id]
            if queue.voice_client and queue.voice_client.is_playing():
                queue.voice_client.stop()
                await interaction.response.send_message("⏭️ 已跳過當前歌曲")
            else:
                await interaction.response.send_message("❌ 目前沒有在播放音樂", ephemeral=True)
        else:
            await interaction.response.send_message("❌ 目前沒有在播放音樂", ephemeral=True)

    @app_commands.command(name="leave", description="讓機器人離開語音頻道")
    async def leave(self, interaction: discord.Interaction):
        if interaction.guild.voice_client:
            if interaction.guild_id in queues:
                queues[interaction.guild_id].clear()
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("👋 已離開語音頻道！")
        else:
            await interaction.response.send_message("❌ 機器人不在語音頻道中！", ephemeral=True)

    @app_commands.command(name="queue", description="顯示當前播放佇列")
    async def queue(self, interaction: discord.Interaction):
        if interaction.guild_id not in queues:
            await interaction.response.send_message("播放佇列是空的！", ephemeral=True)
            return
        
        queue = queues[interaction.guild_id]
        if not queue.queue and not queue.current:
            await interaction.response.send_message("播放佇列是空的！", ephemeral=True)
            return
        
        embed = discord.Embed(title="🎵 播放佇列", color=discord.Color.blue())
        
        # 顯示當前播放的歌曲
        if queue.current:
            embed.add_field(
                name="正在播放",
                value=f"🎵 {html.unescape(queue.current['title'])}",
                inline=False
            )
        
        # 顯示佇列中的歌曲
        if queue.queue:
            queue_text = ""
            for i, song in enumerate(queue.queue, 1):
                queue_text += f"{i}. {html.unescape(song['title'])}\n"
            embed.add_field(name="即將播放", value=queue_text, inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pause", description="暫停當前播放的音樂")
    async def pause(self, interaction: discord.Interaction):
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.pause()
            await interaction.response.send_message("⏸️ 已暫停播放")
        else:
            await interaction.response.send_message("❌ 目前沒有在播放音樂", ephemeral=True)

    @app_commands.command(name="resume", description="恢復播放音樂")
    async def resume(self, interaction: discord.Interaction):
        if interaction.guild.voice_client and interaction.guild.voice_client.is_paused():
            interaction.guild.voice_client.resume()
            await interaction.response.send_message("▶️ 已恢復播放")
        else:
            await interaction.response.send_message("❌ 音樂並未暫停", ephemeral=True)

    @app_commands.command(name="stop", description="停止播放並清空播放佇列")
    async def stop(self, interaction: discord.Interaction):
        if interaction.guild_id in queues:
            queue = queues[interaction.guild_id]
            queue.clear()
            if queue.voice_client:
                queue.voice_client.stop()
            await interaction.response.send_message("⏹️ 已停止播放並清空佇列")
        else:
            await interaction.response.send_message("❌ 目前沒有在播放音樂", ephemeral=True)

    @app_commands.command(name="clear_queue", description="清空播放佇列")
    async def clear_queue(self, interaction: discord.Interaction):
        if interaction.guild_id in queues:
            queue = queues[interaction.guild_id]
            queue.queue.clear()
            await interaction.response.send_message("🗑️ 已清空播放佇列")
        else:
            await interaction.response.send_message("播放佇列已經是空的！", ephemeral=True)

    @app_commands.command(name="volume", description="調整音量 (0-100)")
    async def volume(self, interaction: discord.Interaction, volume: int):
        if not 0 <= volume <= 100:
            await interaction.response.send_message("❌ 音量必須在 0-100 之間", ephemeral=True)
            return
        
        if interaction.guild.voice_client:
            if interaction.guild_id in queues:
                queue = queues[interaction.guild_id]
                if queue.voice_client:
                    queue.voice_client.source.volume = volume / 100
                    await interaction.response.send_message(f"🔊 音量已設定為 {volume}%")
                    return
        
        await interaction.response.send_message("❌ 目前沒有在播放音樂", ephemeral=True)

    @app_commands.command(name="now_playing", description="顯示當前播放的歌曲")
    async def now_playing(self, interaction: discord.Interaction):
        if interaction.guild_id in queues:
            queue = queues[interaction.guild_id]
            if queue.current:
                embed = discord.Embed(title="🎵 正在播放", color=discord.Color.blue())
                embed.add_field(
                    name="歌曲",
                    value=f"{html.unescape(queue.current['title'])}",
                    inline=False
                )
                embed.add_field(
                    name="頻道",
                    value=queue.current['channel'],
                    inline=False
                )
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message("❌ 目前沒有在播放音樂", ephemeral=True)
        else:
            await interaction.response.send_message("❌ 目前沒有在播放音樂", ephemeral=True)

async def setup(bot):
    await bot.add_cog(MusicCommands(bot))
