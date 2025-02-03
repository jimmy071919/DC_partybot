import os
import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import logging
import asyncio
import html
import json
import base64
import tempfile
import shutil
from typing import List, Dict, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
import subprocess
import aiohttp
from collections import defaultdict
from queue_manager import QueueManager

# 載入環境變數
load_dotenv()

class MusicQueue:
    """音樂佇列類"""
    def __init__(self):
        self.queue = []
        self.current = None
        self.voice_client = None
        self.is_playing = False
        self.volume = 1.0
        self.loop = False

    @property
    def is_empty(self):
        return len(self.queue) == 0

    def add(self, song):
        self.queue.append(song)

    def get_next(self) -> Optional[Dict]:
        """獲取下一首要播放的歌曲"""
        if self.loop and self.current:
            return self.current
        elif not self.queue:
            return None
        else:
            self.current = self.queue.pop(0)
            return self.current

    def clear(self):
        """清空佇列"""
        self.queue.clear()
        self.current = None
        self.is_playing = False
        self.loop = False

    def skip(self):
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()
        return self.get_next()

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = defaultdict(QueueManager)
        self.logger = logging.getLogger(__name__)
        self.invidious_instances = [
            'https://invidious.snopyta.org',
            'https://invidious.kavin.rocks',
            'https://vid.puffyan.us',
            'https://yt.artemislena.eu',
            'https://invidious.namazso.eu'
        ]
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        """當 Cog 被卸載時關閉 session"""
        asyncio.create_task(self.session.close())

    async def get_video_info(self, video_id: str) -> Optional[Dict[str, Any]]:
        """從 invidious API 獲取影片資訊"""
        for instance in self.invidious_instances:
            try:
                self.logger.info(f"嘗試從 {instance} 獲取影片資訊")
                async with self.session.get(f"{instance}/api/v1/videos/{video_id}", timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.logger.info(f"成功從 {instance} 獲取影片資訊")
                        return data
            except Exception as e:
                self.logger.error(f"從 {instance} 獲取影片資訊時發生錯誤: {str(e)}")
                continue
        return None

    async def get_audio_url(self, video_id: str) -> Optional[str]:
        """從 invidious API 獲取音訊 URL"""
        video_info = await self.get_video_info(video_id)
        if not video_info:
            return None

        # 獲取可用的音訊格式
        adaptiveFormats = video_info.get('adaptiveFormats', [])
        audio_formats = [f for f in adaptiveFormats if f.get('type', '').startswith('audio/')]
        
        if not audio_formats:
            return None

        # 按照比特率排序，選擇最高品質的音訊
        audio_formats.sort(key=lambda x: x.get('bitrate', 0), reverse=True)
        best_audio = audio_formats[0]
        
        self.logger.info(f"已選擇音訊格式: {best_audio.get('type')} ({best_audio.get('bitrate')})")
        return best_audio.get('url')

    async def ensure_voice_connected(self, interaction: discord.Interaction, max_retries: int = 3) -> bool:
        """確保語音連接成功建立"""
        retry_count = 0
        while retry_count < max_retries:
            try:
                if not interaction.guild.voice_client:
                    self.logger.info(f"嘗試連接語音頻道 (嘗試 {retry_count + 1}/{max_retries})")
                    
                    # 檢查用戶是否在語音頻道中
                    if not interaction.user.voice:
                        self.logger.error("用戶不在語音頻道中")
                        return False
                        
                    # 檢查權限
                    permissions = interaction.user.voice.channel.permissions_for(interaction.guild.me)
                    if not permissions.connect or not permissions.speak:
                        self.logger.error("機器人缺少必要的語音頻道權限")
                        return False
                    
                    # 連接前先等待一下
                    await asyncio.sleep(1)
                    
                    # 嘗試連接
                    voice_client = await interaction.user.voice.channel.connect(timeout=20.0, self_deaf=True)
                    
                    # 等待確保連接完全建立
                    for _ in range(5):  # 最多等待5秒
                        if voice_client and voice_client.is_connected():
                            self.logger.info("語音連接成功建立")
                            # 更新佇列中的語音客戶端
                            queue = self.get_queue(interaction.guild.id)
                            queue.voice_client = voice_client
                            return True
                        await asyncio.sleep(1)
                else:
                    # 檢查現有連接是否有效
                    voice_client = interaction.guild.voice_client
                    if voice_client.is_connected():
                        # 更新佇列中的語音客戶端
                        queue = self.get_queue(interaction.guild.id)
                        queue.voice_client = voice_client
                        return True
                    else:
                        # 斷開無效連接並重試
                        await voice_client.disconnect(force=True)
                        await asyncio.sleep(2)  # 等待更長時間
                        continue

            except discord.ClientException as e:
                self.logger.error(f"Discord 客戶端錯誤 (嘗試 {retry_count + 1}/{max_retries}): {str(e)}")
            except discord.errors.ConnectionClosed as e:
                self.logger.error(f"連接關閉 (嘗試 {retry_count + 1}/{max_retries}): 錯誤碼 {e.code}")
            except Exception as e:
                self.logger.error(f"語音連接失敗 (嘗試 {retry_count + 1}/{max_retries}): {str(e)}")
            
            retry_count += 1
            if retry_count < max_retries:
                await asyncio.sleep(2)  # 增加重試間隔
                continue

        self.logger.error("無法建立語音連接")
        return False

    async def play_next(self, guild_id: int, interaction: discord.Interaction = None):
        """播放下一首歌曲"""
        queue = self.get_queue(guild_id)
        if not queue:
            self.logger.error(f"找不到 guild_id {guild_id} 的佇列")
            return

        # 檢查並嘗試恢復語音客戶端
        if not queue.voice_client and interaction and interaction.guild.voice_client:
            queue.voice_client = interaction.guild.voice_client
            self.logger.info("已恢復語音客戶端連接")

        next_song = queue.get_next()
        if next_song:
            try:
                self.logger.info(f"準備播放: {next_song['title']} ({next_song['url']})")
                
                # 從 URL 中提取影片 ID
                video_id = next_song['url'].split('watch?v=')[-1]
                
                # 獲取音訊 URL
                audio_url = await self.get_audio_url(video_id)
                if not audio_url:
                    raise Exception("無法獲取音訊 URL")
                
                self.logger.info("成功獲取音訊 URL")
                
                # 播放音訊
                FFMPEG_OPTIONS = {
                    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                    'options': '-vn'
                }
                
                source = await discord.FFmpegOpusAudio.from_probe(
                    audio_url,
                    **FFMPEG_OPTIONS
                )
                
                self.logger.info("成功創建音訊源")
                
                queue.voice_client.play(source, after=lambda e: self.after_playing(e))
                queue.is_playing = True
                
                self.logger.info("開始播放音訊")
                
                if interaction:
                    embed = discord.Embed(
                        title="🎵 正在播放",
                        description=next_song['title'],
                        color=discord.Color.green()
                    )
                    await interaction.followup.send(embed=embed)
                
            except Exception as e:
                self.logger.error(f"處理下一首歌曲時發生錯誤: {type(e).__name__}: {str(e)}")
                if interaction:
                    await interaction.followup.send(f"播放時發生錯誤：{type(e).__name__}: {str(e)}", ephemeral=True)
                # 如果出錯，嘗試播放下一首
                await self.play_next(guild_id, interaction)
        else:
            if queue.loop:
                self.logger.info("佇列為空，但已開啟循環播放")
                # 如果開啟了循環播放，重新將當前歌曲加入佇列
                if queue.current:
                    queue.add(queue.current)
                    await self.play_next(guild_id, interaction)
            else:
                self.logger.info("佇列為空且未開啟循環播放")
                queue.is_playing = False
                if interaction:
                    await interaction.followup.send("播放完畢！", ephemeral=True)

    async def search_youtube(self, query: str) -> List[Dict]:
        """搜尋 YouTube 影片"""
        try:
            # 首先嘗試使用 YouTube API
            if self.youtube:
                try:
                    self.logger.info(f"使用 YouTube API 搜尋: {query}")
                    request = self.youtube.search().list(
                        part="snippet",
                        q=query,
                        type="video",
                        maxResults=10
                    )
                    response = request.execute()
                    
                    if not response.get('items'):
                        self.logger.warning("YouTube API 未返回任何結果")
                        return []
                        
                    videos = []
                    for item in response['items']:
                        video_id = item['id']['videoId']
                        title = html.unescape(item['snippet']['title'])  # 解碼 HTML 實體
                        videos.append({
                            'title': title,
                            'url': f'https://www.youtube.com/watch?v={video_id}',
                            'webpage_url': f'https://www.youtube.com/watch?v={video_id}'
                        })
                    
                    self.logger.info(f"使用 YouTube API 搜尋到 {len(videos)} 個影片")
                    return videos
                    
                except Exception as e:
                    self.logger.error(f"YouTube API 搜尋失敗: {str(e)}")
                    # 如果 API 失敗，回退到使用 yt-dlp
                    
            # 使用 yt-dlp 作為備用方案
            self.logger.info(f"使用 yt-dlp 搜尋: {query}")
            
            search_opts = {
                'format': 'bestaudio/best',
                'quiet': False,  # 開啟詳細輸出
                'no_warnings': False,  # 顯示警告
                'extract_flat': False,
                'force_generic_extractor': False,
                'ignoreerrors': False,  # 不忽略錯誤
                'no_color': True,
                'geo_bypass': True,
            }

            with yt_dlp.YoutubeDL(search_opts) as ydl:
                try:
                    self.logger.info("使用的 yt-dlp 選項: {search_opts}")
                    results = ydl.extract_info(f"ytsearch{10}:{query}", download=False)
                    
                    if not results:
                        self.logger.warning("yt-dlp 未返回任何結果")
                        return []
                        
                    videos = []
                    for entry in results['entries']:
                        if entry:
                            title = html.unescape(entry.get('title', 'Unknown Title'))  # 解碼 HTML 實體
                            videos.append({
                                'title': title,
                                'url': entry.get('webpage_url', ''),
                                'webpage_url': entry.get('webpage_url', '')
                            })
                    
                    self.logger.info(f"使用 yt-dlp 搜尋到 {len(videos)} 個影片")
                    return videos
                    
                except Exception as e:
                    self.logger.error(f"yt-dlp 搜尋失敗: {str(e)}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"搜尋過程發生錯誤: {str(e)}")
            return []

    class SongSelectView(discord.ui.View):
        def __init__(self, videos: List[Dict], cog):
            super().__init__(timeout=30.0)
            self.videos = videos
            self.cog = cog
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
                if interaction.user != self.cog.original_user:
                    await interaction.response.send_message("只有發起播放的用戶可以選擇歌曲！", ephemeral=True)
                    return
                    
                self.selected_song = self.videos[index]
                self.selected_song['requester'] = interaction.user.display_name
                self.stop()
                
                # 禁用所有按鈕
                for item in self.children:
                    item.disabled = True
                await interaction.response.edit_message(view=self)
                
                # 獲取佇列
                queue = self.cog.get_queue(interaction.guild.id)
                
                # 添加到佇列
                queue.queue.append(self.selected_song)
                
                # 如果沒有正在播放，則開始播放
                if not queue.is_playing:
                    await self.cog.play_next(interaction.guild.id, interaction)
                else:
                    # 如果已經在播放，則發送已加入佇列的消息
                    embed = discord.Embed(
                        title="🎵 已加入播放佇列",
                        description=self.selected_song['title'],
                        color=discord.Color.green()
                    )
                    embed.add_field(
                        name="請求者",
                        value=self.selected_song['requester']
                    )
                    await interaction.followup.send(embed=embed)
                    
            return button_callback

        async def on_timeout(self):
            # 禁用所有按鈕
            for item in self.children:
                item.disabled = True
            # 注意：這裡需要一個有效的 interaction 來更新消息
            if self.message:
                await self.message.edit(view=self)

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
    async def play(self, interaction: discord.Interaction, *, query: str):
        """播放音樂"""
        try:
            # 檢查用戶是否在語音頻道中
            if not interaction.user.voice:
                await interaction.response.send_message("你必須先加入一個語音頻道！", ephemeral=True)
                return
                
            # 檢查機器人是否有權限加入語音頻道
            permissions = interaction.user.voice.channel.permissions_for(interaction.guild.me)
            if not permissions.connect or not permissions.speak:
                await interaction.response.send_message("我沒有權限加入該語音頻道！", ephemeral=True)
                return

            # 檢查機器人是否已經在其他語音頻道中
            if interaction.guild.voice_client:
                if interaction.guild.voice_client.channel != interaction.user.voice.channel:
                    await interaction.response.send_message("我已經在另一個語音頻道中了！", ephemeral=True)
                    return

            # 延遲響應，因為接下來的操作可能需要一些時間
            try:
                await interaction.response.defer(ephemeral=False)
            except discord.errors.InteractionResponded:
                pass

            # 確保語音連接
            if not await self.ensure_voice_connected(interaction):
                await interaction.followup.send("無法建立語音連接，請稍後再試！", ephemeral=True)
                return

            # 搜索視頻
            try:
                videos = await self.search_youtube(query)
                if not videos:
                    await interaction.followup.send("找不到相關影片！", ephemeral=True)
                    return

                # 創建嵌入式消息顯示搜索結果
                embed = discord.Embed(
                    title="🎵 YouTube 搜尋結果",
                    description="請選擇要播放的歌曲：",
                    color=discord.Color.blue()
                )
                
                # 只顯示前5個結果
                for i, video in enumerate(videos[:5], 1):
                    embed.add_field(
                        name=f"{i}. {video['title']}", 
                        value=f"[點擊觀看]({video['url']})", 
                        inline=False
                    )

                # 保存原始用戶
                self.original_user = interaction.user
                
                # 創建並發送選擇視圖
                view = self.SongSelectView(videos, self)
                message = await interaction.followup.send(embed=embed, view=view)
                view.message = message  # 保存消息引用以便稍後更新

            except Exception as e:
                self.logger.error(f"搜索時發生錯誤: {str(e)}")
                await interaction.followup.send(f"搜索時發生錯誤：{str(e)}", ephemeral=True)
                return

        except Exception as e:
            self.logger.error(f"播放命令發生錯誤: {str(e)}")
            try:
                await interaction.followup.send(f"發生錯誤：{str(e)}", ephemeral=True)
            except discord.errors.HTTPException:
                if interaction.channel:
                    await interaction.channel.send(f"發生錯誤：{str(e)}")

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
                await interaction.response.send_message("我沒有在任何語音頻道中！", ephemeral=True)
                return

            # 清理佇列
            queue = self.get_queue(interaction.guild.id)
            if queue:
                queue.clear()

            # 斷開連接
            await interaction.guild.voice_client.disconnect(force=True)
            
            try:
                await interaction.response.send_message("👋 機器人已離開語音頻道！")
            except discord.errors.InteractionResponded:
                await interaction.followup.send("👋 機器人已離開語音頻道！")
            
        except Exception as e:
            self.logger.error(f"離開語音頻道時發生錯誤：{str(e)}")
            try:
                await interaction.response.send_message("離開語音頻道時發生錯誤，請稍後再試！", ephemeral=True)
            except discord.errors.InteractionResponded:
                await interaction.followup.send("離開語音頻道時發生錯誤，請稍後再試！", ephemeral=True)

async def setup(bot):
    """設置 Music cog"""
    await bot.add_cog(Music(bot))
