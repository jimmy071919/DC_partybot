import yt_dlp
import logging
import asyncio
import discord
from discord.ext import commands
import tempfile
import os
import base64
import aiohttp
from typing import Optional, Dict, Any
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

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = defaultdict(MusicQueue)
        self.logger = logging.getLogger(__name__)
        self.youtube = build('youtube', 'v3', developerKey=os.getenv('YOUTUBE_API_KEY'))
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

    def get_queue(self, guild_id: int) -> MusicQueue:
        """獲取或創建伺服器的音樂佇列"""
        return self.queues[guild_id]

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
                
                if ctx:
                    embed = discord.Embed(
                        title="🎵 正在播放",
                        description=next_song['title'],
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
                maxResults=10,
                type='video'
            ).execute()
            
            if not search_response.get('items'):
                await ctx.reply("找不到相關影片。", ephemeral=True)
                return
            
            self.logger.info(f"使用 YouTube API 搜尋到 {len(search_response['items'])} 個影片")
            
            # 獲取第一個搜尋結果
            video = search_response['items'][0]
            video_id = video['id']['videoId']
            video_title = video['snippet']['title']
            video_url = f'https://www.youtube.com/watch?v={video_id}'
            
            # 將歌曲加入佇列
            queue = self.get_queue(ctx.guild.id)
            queue.add({
                'title': video_title,
                'url': video_url
            })
            
            # 如果沒有正在播放的歌曲，開始播放
            if not queue.is_playing:
                await self.play_next(ctx.guild.id, ctx)
            else:
                await ctx.reply(f"已將 {video_title} 加入播放佇列！", ephemeral=True)
            
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
