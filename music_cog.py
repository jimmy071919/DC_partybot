import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import html
import yt_dlp
from googleapiclient.discovery import build
import os
from dotenv import load_dotenv
import logging
import shutil

# 載入環境變數
load_dotenv()

class MusicQueue:
    def __init__(self):
        self.queue = []
        self.current = None
        self.voice_client = None
        self.is_playing = False
        self.volume = 1.0  # 新增音量控制
        self._loop = False  # 新增循環播放控制

    @property
    def is_empty(self):
        return len(self.queue) == 0

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    def add(self, song):
        self.queue.append(song)

    def get_next(self):
        if not self.queue:
            return None
        if self._loop and self.current:
            self.queue.append(self.current)
        return self.queue.pop(0)

    def clear(self):
        self.queue.clear()
        self.current = None
        self._loop = False

    def skip(self):
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()
        return self.get_next()

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}
        self.youtube = build('youtube', 'v3', developerKey=os.getenv('YOUTUBE_API_KEY'))
        self.logger = logging.getLogger(__name__)
        
        # 檢查 ffmpeg 是否存在於系統中
        ffmpeg_path = shutil.which('ffmpeg')
        if not ffmpeg_path:
            # 嘗試在常見路徑中尋找 ffmpeg
            common_paths = [
                '/usr/bin/ffmpeg',
                '/usr/local/bin/ffmpeg',
                '/opt/ffmpeg/bin/ffmpeg'
            ]
            for path in common_paths:
                if os.path.exists(path):
                    ffmpeg_path = path
                    break
            
            if not ffmpeg_path:
                self.logger.error("找不到 ffmpeg，音樂功能將無法使用")
                self.logger.warning("音樂功能將被禁用，但其他功能仍然可用")
                self.disabled = True
                return
        
        self.logger.info(f"找到 ffmpeg: {ffmpeg_path}")
        self.disabled = False
        
        # 設定 yt-dlp 選項
        self.YDL_OPTIONS = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'ffmpeg_location': ffmpeg_path,
            'prefer_ffmpeg': True,
            'keepvideo': False,
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {
                'youtube': {
                    'player_skip': ['webpage', 'configs'],
                    'skip': ['webpage']
                }
            }
        }

    def get_queue(self, guild_id: int) -> MusicQueue:
        """獲取或創建伺服器的音樂佇列"""
        if guild_id not in self.queues:
            self.queues[guild_id] = MusicQueue()
        return self.queues[guild_id]

    async def ensure_voice_client(self, interaction: discord.Interaction) -> bool:
        """確保機器人在語音頻道中"""
        if not interaction.guild:
            await interaction.response.send_message("這個指令只能在伺服器中使用！", ephemeral=True)
            return False

        if not interaction.user.voice:
            await interaction.response.send_message("你必須先加入語音頻道！", ephemeral=True)
            return False

        queue = self.get_queue(interaction.guild_id)
        if not queue.voice_client:
            try:
                queue.voice_client = await interaction.user.voice.channel.connect()
            except Exception as e:
                self.logger.error(f"無法連接到語音頻道: {str(e)}")
                await interaction.response.send_message("無法連接到語音頻道，請稍後再試！", ephemeral=True)
                return False

        return True

    async def play_next(self, guild_id: int, interaction: discord.Interaction = None):
        """播放下一首歌曲"""
        queue = self.get_queue(guild_id)
        if not queue.voice_client:
            return

        if not queue.queue and not queue.loop:
            queue.is_playing = False
            queue.current = None
            return

        next_song = queue.get_next()
        if not next_song:
            return

        queue.current = next_song

        try:
            with yt_dlp.YoutubeDL(self.YDL_OPTIONS) as ydl:
                info = ydl.extract_info(next_song['url'], download=False)
                url = info['url']

                def after_playing(error):
                    if error:
                        self.logger.error(f"播放錯誤：{error}")
                    asyncio.run_coroutine_threadsafe(
                        self.play_next(guild_id), 
                        self.bot.loop
                    )

                queue.voice_client.play(
                    discord.FFmpegPCMAudio(url, executable='ffmpeg'),
                    after=after_playing
                )
                queue.voice_client.source = discord.PCMVolumeTransformer(
                    queue.voice_client.source,
                    volume=queue.volume
                )
                queue.is_playing = True

                if interaction and interaction.channel:
                    title = html.unescape(next_song['title'])
                    embed = discord.Embed(
                        title="🎵 正在播放",
                        description=title,
                        color=discord.Color.green()
                    )
                    embed.add_field(
                        name="長度", 
                        value=f"{info.get('duration_string', 'N/A')}"
                    )
                    embed.add_field(
                        name="請求者", 
                        value=next_song.get('requester', 'Unknown')
                    )
                    await interaction.channel.send(embed=embed)

        except Exception as e:
            self.logger.error(f"播放錯誤：{str(e)}")
            if interaction and interaction.channel:
                await interaction.channel.send(f"播放時發生錯誤：{str(e)}")
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

        # 先發送延遲回應
        await interaction.response.defer()

        try:
            videos = self.search_youtube(query)
        except Exception as e:
            await interaction.followup.send("搜尋時發生錯誤！", ephemeral=True)
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
        await interaction.followup.send(embed=embed, view=view)

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
        """讓機器人離開語音頻道"""
        try:
            # 檢查機器人是否在語音頻道中
            if not interaction.guild.voice_client:
                await interaction.response.send_message("機器人不在任何語音頻道內！", ephemeral=True)
                return

            # 檢查用戶是否在同一個語音頻道
            if not interaction.user.voice or interaction.user.voice.channel != interaction.guild.voice_client.channel:
                await interaction.response.send_message("你必須在機器人所在的語音頻道內才能使用此命令！", ephemeral=True)
                return

            # 停止播放並清理隊列
            if interaction.guild_id in self.queues:
                queue = self.queues[interaction.guild_id]
                if queue.voice_client and queue.voice_client.is_playing():
                    queue.voice_client.stop()
                queue.clear()
                del self.queues[interaction.guild_id]

            # 斷開連接
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("👋 機器人已離開語音頻道！")
            
        except Exception as e:
            self.logger.error(f"離開語音頻道時發生錯誤：{str(e)}")
            await interaction.response.send_message("離開語音頻道時發生錯誤，請稍後再試！", ephemeral=True)

async def setup(bot):
    """設置 Music cog"""
    await bot.add_cog(Music(bot))
