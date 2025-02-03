import yt_dlp
import logging
import asyncio
import discord
from discord.ext import commands
import tempfile
import os
import base64
from typing import Optional, Dict, Any, List
from collections import defaultdict
from googleapiclient.discovery import build

class MusicQueue:
    def __init__(self):
        self.queue = []
        self.current = None
        self.voice_client = None
        self.is_playing = False
        self.loop = False

    def add(self, item):
        self.queue.append(item)

    def get_next(self):
        if not self.queue:
            return None
        self.current = self.queue.pop(0)
        return self.current

class SongSelectView(discord.ui.View):
    def __init__(self, videos: List[Dict], cog, ctx: commands.Context):
        super().__init__(timeout=30.0)
        self.videos = videos
        self.cog = cog
        self.ctx = ctx
        self.selected_song = None
        
        # 只顯示前5個結果的按鈕
        for i in range(min(5, len(videos))):
            button = discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label=str(i + 1),
                custom_id=str(i)
            )
            button.callback = self.create_callback(i)
            self.add_item(button)

    def create_callback(self, index: int):
        async def button_callback(interaction: discord.Interaction):
            if interaction.user != self.ctx.author:
                await interaction.response.send_message("只有發起播放的用戶可以選擇歌曲！", ephemeral=True)
                return
                
            self.selected_song = self.videos[index]
            self.stop()
            
            # 禁用所有按鈕
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(view=self)
            
            # 獲取佇列
            queue = self.cog.get_queue(interaction.guild.id)
            
            # 添加到佇列
            queue.add(self.selected_song)
            
            # 如果沒有正在播放，則開始播放
            if not queue.is_playing:
                await self.cog.play_next(interaction.guild.id, self.ctx)
            else:
                # 如果已經在播放，則發送已加入佇列的消息
                embed = discord.Embed(
                    title="🎵 已加入播放佇列",
                    description=self.selected_song['title'],
                    color=discord.Color.green()
                )
                await interaction.followup.send(embed=embed)
                
        return button_callback

    async def on_timeout(self):
        # 禁用所有按鈕
        for item in self.children:
            item.disabled = True
        # 注意：這裡需要一個有效的 interaction 來更新消息
        if hasattr(self, 'message'):
            await self.message.edit(view=self)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = defaultdict(MusicQueue)
        self.logger = logging.getLogger(__name__)
        self.youtube = build('youtube', 'v3', developerKey=os.getenv('YOUTUBE_API_KEY'))
        
        # 設置 yt-dlp 選項
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'force_generic_extractor': False,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'no_color': True,
            'geo_bypass': True,
            'socket_timeout': 30,
            'retries': 10
        }

    def get_queue(self, guild_id: int) -> MusicQueue:
        """獲取或創建伺服器的音樂佇列"""
        return self.queues[guild_id]

    async def ensure_voice_connected(self, ctx) -> bool:
        """確保語音連接成功建立"""
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                # 檢查用戶是否在語音頻道中
                if not ctx.author.voice:
                    self.logger.error("用戶不在語音頻道中")
                    await ctx.reply("你必須先加入一個語音頻道！", ephemeral=True)
                    return False
                
                # 檢查機器人是否已經在語音頻道中
                if not ctx.guild.voice_client:
                    self.logger.info(f"嘗試連接語音頻道 (嘗試 {retry_count + 1}/{max_retries})")
                    
                    # 連接到語音頻道
                    try:
                        voice_client = await ctx.author.voice.channel.connect()
                        self.logger.info("語音連接成功建立")
                        return True
                    except Exception as e:
                        self.logger.error(f"連接語音頻道時發生錯誤: {str(e)}")
                        retry_count += 1
                        if retry_count < max_retries:
                            await asyncio.sleep(1)  # 等待一秒後重試
                            continue
                        else:
                            await ctx.reply("無法連接到語音頻道，請稍後再試。", ephemeral=True)
                            return False
                else:
                    self.logger.info("機器人已經在語音頻道中")
                    return True
                
            except Exception as e:
                self.logger.error(f"確保語音連接時發生錯誤: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    await asyncio.sleep(1)
                    continue
                else:
                    await ctx.reply("發生錯誤，請稍後再試。", ephemeral=True)
                    return False
        
        return False

    async def after_playing(self, error):
        """當一首歌播放完畢時的回調函數"""
        if error:
            self.logger.error(f"播放時發生錯誤: {str(error)}")
        
        for guild_id, queue in self.queues.items():
            if queue.voice_client and not queue.voice_client.is_playing():
                asyncio.create_task(self.play_next(guild_id))

    async def get_audio_url(self, url: str) -> Optional[Dict[str, str]]:
        """使用 yt-dlp 獲取音訊 URL"""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: ydl.extract_info(url, download=False)
                )
                if not info:
                    return None
                    
                return {
                    'url': info['url'],
                    'title': info['title']
                }
        except Exception as e:
            self.logger.error(f"獲取音訊 URL 時發生錯誤: {str(e)}")
            return None

    async def play_next(self, guild_id: int, ctx = None):
        """播放下一首歌曲"""
        queue = self.get_queue(guild_id)
        if not queue:
            self.logger.error(f"找不到 guild_id {guild_id} 的佇列")
            return

        # 檢查並嘗試恢復語音客戶端
        if not queue.voice_client and ctx and ctx.guild.voice_client:
            queue.voice_client = ctx.guild.voice_client
            self.logger.info("已恢復語音客戶端連接")

        next_song = queue.get_next()
        if next_song:
            try:
                self.logger.info(f"準備播放: {next_song['title']} ({next_song['url']})")
                
                # 獲取音訊 URL
                audio_info = await self.get_audio_url(next_song['url'])
                if not audio_info:
                    raise Exception("無法獲取音訊 URL")
                
                self.logger.info("成功獲取音訊 URL")
                
                # 播放音訊
                FFMPEG_OPTIONS = {
                    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                    'options': '-vn'
                }
                
                source = await discord.FFmpegOpusAudio.from_probe(
                    audio_info['url'],
                    **FFMPEG_OPTIONS
                )
                
                self.logger.info("成功創建音訊源")
                
                queue.voice_client.play(source, after=lambda e: self.after_playing(e))
                queue.is_playing = True
                
                self.logger.info("開始播放音訊")
                
                if ctx:
                    embed = discord.Embed(
                        title="🎵 正在播放",
                        description=audio_info['title'],
                        color=discord.Color.green()
                    )
                    await ctx.reply(embed=embed)
                
            except Exception as e:
                self.logger.error(f"處理下一首歌曲時發生錯誤: {type(e).__name__}: {str(e)}")
                if ctx:
                    await ctx.reply(f"播放時發生錯誤：{type(e).__name__}: {str(e)}", ephemeral=True)
                # 如果出錯，嘗試播放下一首
                await self.play_next(guild_id, ctx)
        else:
            if queue.loop:
                self.logger.info("佇列為空，但已開啟循環播放")
                # 如果開啟了循環播放，重新將當前歌曲加入佇列
                if queue.current:
                    queue.add(queue.current)
                    await self.play_next(guild_id, ctx)
            else:
                self.logger.info("佇列為空且未開啟循環播放")
                queue.is_playing = False
                if ctx:
                    await ctx.reply("播放完畢！", ephemeral=True)

    @commands.hybrid_command(name='play', description='播放音樂')
    async def play(self, ctx: commands.Context, *, query: str):
        """播放音樂"""
        # 延遲回應
        await ctx.defer()
        
        # 檢查是否已經連接到語音頻道
        if not await self.ensure_voice_connected(ctx):
            return
            
        try:
            # 使用 YouTube API 搜尋影片
            self.logger.info(f"使用 YouTube API 搜尋: {query}")
            
            search_response = self.youtube.search().list(
                q=query,
                part='id,snippet',
                maxResults=5,
                type='video'
            ).execute()
            
            if not search_response.get('items'):
                await ctx.reply("找不到相關影片。", ephemeral=True)
                return
            
            self.logger.info(f"使用 YouTube API 搜尋到 {len(search_response['items'])} 個影片")
            
            # 創建搜尋結果列表
            videos = []
            for item in search_response['items']:
                video_id = item['id']['videoId']
                video_title = item['snippet']['title']
                video_url = f'https://www.youtube.com/watch?v={video_id}'
                videos.append({
                    'title': video_title,
                    'url': video_url
                })
            
            # 創建嵌入式消息顯示搜索結果
            embed = discord.Embed(
                title="🎵 YouTube 搜尋結果",
                description="請選擇要播放的歌曲：",
                color=discord.Color.blue()
            )
            
            for i, video in enumerate(videos, 1):
                embed.add_field(
                    name=f"{i}. {video['title']}", 
                    value=f"[點擊觀看]({video['url']})", 
                    inline=False
                )
            
            # 創建並發送選擇視圖
            view = SongSelectView(videos, self, ctx)
            message = await ctx.reply(embed=embed, view=view)
            view.message = message  # 保存消息引用以便稍後更新
            
        except Exception as e:
            self.logger.error(f"播放指令發生錯誤: {str(e)}")
            await ctx.reply(f"發生錯誤：{str(e)}", ephemeral=True)

    @commands.hybrid_command(name='skip', description='跳過當前歌曲')
    async def skip(self, ctx: commands.Context):
        """跳過當前歌曲"""
        await ctx.defer()
        
        queue = self.get_queue(ctx.guild.id)
        if queue.voice_client and queue.voice_client.is_playing():
            queue.voice_client.stop()
            await ctx.reply("已跳過當前歌曲！", ephemeral=True)
        else:
            await ctx.reply("目前沒有正在播放的歌曲。", ephemeral=True)

    @commands.hybrid_command(name='loop', description='切換循環播放模式')
    async def loop(self, ctx: commands.Context):
        """切換循環播放模式"""
        await ctx.defer()
        
        queue = self.get_queue(ctx.guild.id)
        queue.loop = not queue.loop
        await ctx.reply(f"循環播放模式已{'開啟' if queue.loop else '關閉'}！", ephemeral=True)

    @commands.hybrid_command(name='stop', description='停止播放並清空佇列')
    async def stop(self, ctx: commands.Context):
        """停止播放並清空佇列"""
        await ctx.defer()
        
        queue = self.get_queue(ctx.guild.id)
        if queue.voice_client:
            queue.voice_client.stop()
            await queue.voice_client.disconnect()
            queue.queue.clear()
            queue.current = None
            queue.is_playing = False
            await ctx.reply("已停止播放並清空佇列！", ephemeral=True)
        else:
            await ctx.reply("機器人不在語音頻道中。", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Music(bot))
