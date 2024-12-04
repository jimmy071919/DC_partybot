import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import html
import yt_dlp
from googleapiclient.discovery import build
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

class MusicQueue:
    def __init__(self):
        self.queue = []
        self.current = None
        self.voice_client = None
        self.is_playing = False

    def add(self, song):
        self.queue.append(song)

    def get_next(self):
        if self.queue:
            return self.queue.pop(0)
        return None

    def clear(self):
        self.queue.clear()
        self.current = None

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}  # 為每個伺服器建立獨立的播放佇列
        self.tree = bot.tree
        self.youtube = build('youtube', 'v3', developerKey=os.getenv('YOUTUBE_API_KEY'))

    async def play_next(self, guild_id, interaction=None):
        if guild_id not in self.queues:
            return
        
        queue = self.queues[guild_id]
        
        if not queue.queue:
            queue.is_playing = False
            queue.current = None
            return
        
        next_song = queue.get_next()
        queue.current = next_song
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'ffmpeg_location': 'ffmpeg',  # 直接使用系統 ffmpeg
            'prefer_ffmpeg': True,
            'keepvideo': False
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(next_song['url'], download=False)
                url = info['url']
                
                def after_playing(error):
                    if error:
                        print(f"播放錯誤：{error}")
                    asyncio.run_coroutine_threadsafe(self.play_next(guild_id), self.bot.loop)
                
                queue.voice_client.play(discord.FFmpegPCMAudio(url, executable='ffmpeg'), after=after_playing)
                queue.is_playing = True
                
                if interaction:
                    title = html.unescape(next_song['title'])
                    asyncio.run_coroutine_threadsafe(
                        interaction.channel.send(f"🎵 正在播放：{title}"),
                        self.bot.loop
                    )
                
        except Exception as e:
            print(f"播放錯誤：{e}")
            await self.play_next(guild_id, interaction)

    def search_youtube(self, query):
        request = self.youtube.search().list(
            part="snippet",
            q=query,
            type="video",
            maxResults=10
        )
        response = request.execute()
        
        videos = []
        for item in response['items']:
            video = {
                "title": item['snippet']['title'],
                "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                "channel": item['snippet']['channelTitle']
            }
            videos.append(video)
        return videos

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
            videos = self.search_youtube(query)
        except Exception as e:
            await interaction.response.send_message("搜尋時發生錯誤！", ephemeral=True)
            return

        embed = discord.Embed(title="YouTube 搜尋結果", color=discord.Color.blue())
        for i, video in enumerate(videos):
            embed.add_field(
                name=f"{i+1}. {html.unescape(video['title'])}", 
                value=f"頻道: {video['channel']}\n[點擊觀看]({video['url']})", 
                inline=False
            )

        class SongSelectView(discord.ui.View):
            def __init__(self, videos, cog):
                super().__init__(timeout=30.0)
                self.videos = videos
                self.cog = cog
                self.selected_song = None

            @discord.ui.button(label="1", style=discord.ButtonStyle.primary)
            async def button1_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.handle_button_click(interaction, 0)

            @discord.ui.button(label="2", style=discord.ButtonStyle.primary)
            async def button2_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.handle_button_click(interaction, 1)

            @discord.ui.button(label="3", style=discord.ButtonStyle.primary)
            async def button3_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.handle_button_click(interaction, 2)

            @discord.ui.button(label="4", style=discord.ButtonStyle.primary)
            async def button4_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.handle_button_click(interaction, 3)

            @discord.ui.button(label="5", style=discord.ButtonStyle.primary)
            async def button5_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.handle_button_click(interaction, 4)

            @discord.ui.button(label="6", style=discord.ButtonStyle.primary)
            async def button6_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.handle_button_click(interaction, 5)

            @discord.ui.button(label="7", style=discord.ButtonStyle.primary)
            async def button7_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.handle_button_click(interaction, 6)

            @discord.ui.button(label="8", style=discord.ButtonStyle.primary)
            async def button8_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.handle_button_click(interaction, 7)

            @discord.ui.button(label="9", style=discord.ButtonStyle.primary)
            async def button9_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.handle_button_click(interaction, 8)

            @discord.ui.button(label="10", style=discord.ButtonStyle.primary)
            async def button10_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.handle_button_click(interaction, 9)

            async def handle_button_click(self, interaction: discord.Interaction, index: int):
                self.selected_song = self.videos[index]
                self.stop()
                await self.handle_song_selection(interaction)

            async def handle_song_selection(self, interaction: discord.Interaction):
                if interaction.guild_id not in self.cog.queues:
                    self.cog.queues[interaction.guild_id] = MusicQueue()
                
                queue = self.cog.queues[interaction.guild_id]
                
                song = {
                    "title": html.unescape(self.selected_song["title"]),
                    "url": self.selected_song["url"]
                }
                
                if not queue.voice_client or not queue.voice_client.is_connected():
                    try:
                        queue.voice_client = await interaction.user.voice.channel.connect()
                    except discord.ClientException:
                        queue.voice_client = interaction.guild.voice_client
                
                queue.add(song)
                
                if not queue.is_playing:
                    await interaction.response.send_message(f"🎵 即將播放：{song['title']}")
                    await self.cog.play_next(interaction.guild_id, interaction)
                else:
                    await interaction.response.send_message(f"🎵 已加入播放佇列：{song['title']}")

            async def on_timeout(self):
                for child in self.children:
                    child.disabled = True

        view = SongSelectView(videos, self)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="queue", description="顯示目前的播放佇列")
    async def show_queue(self, interaction: discord.Interaction):
        if interaction.guild_id not in self.queues:
            await interaction.response.send_message("播放佇列是空的！", ephemeral=True)
            return
        
        queue = self.queues[interaction.guild_id]
        
        if not queue.current and not queue.queue:
            await interaction.response.send_message("播放佇列是空的！", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🎵 播放佇列",
            color=discord.Color.blue()
        )
        
        if queue.current:
            embed.add_field(
                name="正在播放",
                value=f"🎵 {html.unescape(queue.current['title'])}",
                inline=False
            )
        
        if queue.queue:
            queue_text = "\n".join([f"{i+1}. {html.unescape(song['title'])}" for i, song in enumerate(queue.queue)])
            embed.add_field(
                name="即將播放",
                value=queue_text,
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="skip", description="跳過目前播放的歌曲")
    async def skip(self, interaction: discord.Interaction):
        if interaction.guild_id not in self.queues:
            await interaction.response.send_message("目前沒有正在播放的音樂！", ephemeral=True)
            return
        
        queue = self.queues[interaction.guild_id]
        
        if not queue.is_playing:
            await interaction.response.send_message("目前沒有正在播放的音樂！", ephemeral=True)
            return
        
        queue.voice_client.stop()
        await interaction.response.send_message("⏭️ 已跳過當前歌曲")

    @app_commands.command(name="clear_queue", description="清除播放佇列")
    async def clear_queue(self, interaction: discord.Interaction):
        if interaction.guild_id not in self.queues:
            await interaction.response.send_message("播放佇列已經是空的！", ephemeral=True)
            return
        
        queue = self.queues[interaction.guild_id]
        queue.clear()
        
        if queue.voice_client and queue.voice_client.is_playing():
            queue.voice_client.stop()
        
        await interaction.response.send_message("🗑️ 已清除播放佇列")

    @app_commands.command(name="pause", description="暫停播放的音樂")
    async def pause(self, interaction: discord.Interaction):
        if interaction.guild_id not in self.queues:
            await interaction.response.send_message("目前沒有正在播放的音樂！", ephemeral=True)
            return
        
        queue = self.queues[interaction.guild_id]
        
        if not queue.is_playing:
            await interaction.response.send_message("目前沒有正在播放的音樂！", ephemeral=True)
            return
        
        queue.voice_client.pause()
        await interaction.response.send_message("音樂已暫停！")

    @app_commands.command(name="resume", description="繼續播放已暫停的音樂")
    async def resume(self, interaction: discord.Interaction):
        if interaction.guild_id not in self.queues:
            await interaction.response.send_message("目前沒有正在播放的音樂！", ephemeral=True)
            return
        
        queue = self.queues[interaction.guild_id]
        
        if not queue.is_playing:
            await interaction.response.send_message("目前沒有正在播放的音樂！", ephemeral=True)
            return
        
        queue.voice_client.resume()
        await interaction.response.send_message("音樂已繼續播放！")

    @app_commands.command(name="stop", description="停止播放的音樂")
    async def stop(self, interaction: discord.Interaction):
        if interaction.guild_id not in self.queues:
            await interaction.response.send_message("目前沒有正在播放的音樂！", ephemeral=True)
            return
        
        queue = self.queues[interaction.guild_id]
        
        if not queue.is_playing:
            await interaction.response.send_message("目前沒有正在播放的音樂！", ephemeral=True)
            return
        
        queue.voice_client.stop()
        await interaction.response.send_message("音樂已停止！")

    @app_commands.command(name="leave", description="讓機器人離開語音頻道")
    async def leave(self, interaction: discord.Interaction):
        if interaction.guild_id not in self.queues:
            await interaction.response.send_message("機器人不在任何語音頻道內！", ephemeral=True)
            return
        
        queue = self.queues[interaction.guild_id]
        
        if queue.voice_client:
            await queue.voice_client.disconnect()
            await interaction.response.send_message("機器人已離開語音頻道！")
        else:
            await interaction.response.send_message("機器人不在任何語音頻道內！", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Music(bot))
