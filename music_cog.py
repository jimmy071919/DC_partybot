import yt_dlp
import logging
import asyncio
import discord
from discord.ext import commands, tasks
import tempfile
import os
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from collections import defaultdict
from googleapiclient.discovery import build
import ssl
import certifi

class MusicQueue:
    """音樂佇列類 - 管理每個伺服器的音樂播放佇列
    
    優化版本增加了佇列診斷和管理功能
    """
    def __init__(self):
        self.queue = []          # 歌曲佇列
        self.current = None      # 當前播放的歌曲
        self.voice_client = None # 語音客戶端連接
        self.is_playing = False  # 是否正在播放
        self.loop = False        # 循環播放模式
        self.last_updated = None # 最後更新時間
    
    def __str__(self):
        """返回佇列的字符串表示以便診斷"""
        status = "播放中" if self.is_playing else "暫停"
        loop = "開啟" if self.loop else "關閉"
        current = self.current["title"] if self.current else "無"
        return f"佇列狀態: {status} | 循環模式: {loop} | 佇列長度: {len(self.queue)} | 當前歌曲: {current}"
    
    def add(self, item):
        """新增歌曲到佇列"""
        self.queue.append(item)
        self.last_updated = datetime.now()
        return len(self.queue)  # 返回佇列長度方便提示

    def get_next(self):
        """獲取佇列中的下一首歌曲"""
        if not self.queue:
            return None
        self.current = self.queue.pop(0)
        self.last_updated = datetime.now()
        return self.current
        
    def clear(self):
        """清空佇列"""
        self.queue = []
        self.current = None
        self.is_playing = False
        self.last_updated = datetime.now()
        
    def add_to_front(self, item):
        """將歌曲添加到佇列的最前面（下一首播放）"""
        self.queue.insert(0, item)
        self.last_updated = datetime.now()
        
    def get_queue_info(self):
        """獲取佇列資訊，用於顯示給用戶"""
        info = []
        if self.current:
            info.append(f"▶️ 正在播放: {self.current['title']}")
        if self.queue:
            info.append("\n📋 即將播放:")
            for i, song in enumerate(self.queue, 1):
                if i <= 10:  # 只顯示前10首
                    info.append(f"{i}. {song['title']}")
                else:
                    info.append(f"...以及更多 {len(self.queue) - 10} 首歌曲")
                    break
        return "\n".join(info) if info else "佇列為空"

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
        
        # 設置 SSL 憑證處理
        self._setup_ssl()
        
        # 初始化 YouTube API 客戶端，帶有重試機制
        self.youtube = self._initialize_youtube_api()
        
        # 啟動自動檢查語音頻道的任務
        self.check_voice_activity.start()
        
        # 設置 yt-dlp 選項 - 優化音訊提取和錯誤處理
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
            'retries': 10,
            'source_address': '0.0.0.0',  # 綁定到 IPv4
            'prefer_insecure': True,  # 強制使用 HTTP 而非 HTTPS（如果可能）
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            },
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'opus',
                'preferredquality': '192',
            }],
            'default_search': 'auto',
            'logtostderr': False,
            'verbose': False,
            # 不使用 cookie 檔案，避免格式問題
            'cookiefile': None,
        }
        
    def _setup_ssl(self):
        """設置 SSL 憑證驗證，解決憑證問題"""
        try:
            import ssl
            import os
            
            # 設置環境變數來避免 SSL 驗證問題
            os.environ['PYTHONHTTPSVERIFY'] = '0'
            os.environ['CURL_CA_BUNDLE'] = ''
            os.environ['REQUESTS_CA_BUNDLE'] = ''
            
            # 設置默認 SSL 上下文使用不驗證模式
            ssl._create_default_https_context = ssl._create_unverified_context
            
            # 嘗試安裝 certifi 如果可用的話
            try:
                import certifi
                os.environ['SSL_CERT_FILE'] = certifi.where()
                self.logger.info("已設置 SSL 憑證路徑使用 certifi")
            except ImportError:
                self.logger.warning("未安裝 certifi 套件，使用不驗證模式")
            
            self.logger.info("已設置 SSL 憑證上下文為不驗證模式")
        except Exception as e:
            self.logger.error(f"設置 SSL 憑證時發生錯誤: {str(e)}")

    def _initialize_youtube_api(self):
        """初始化 YouTube API 客戶端，帶有 SSL 錯誤處理"""
        try:
            import httplib2
            from googleapiclient.discovery import build
            
            # 檢查 API 金鑰
            api_key = os.getenv('YOUTUBE_API_KEY')
            if not api_key:
                self.logger.error("YOUTUBE_API_KEY 環境變數未設定")
                return None
            else:
                self.logger.info(f"YouTube API 金鑰已載入 (長度: {len(api_key)})")
            
            # 創建自定義的 HTTP 對象，禁用 SSL 驗證
            http = httplib2.Http(disable_ssl_certificate_validation=True)
            
            # 設置額外的 SSL 環境
            os.environ['PYTHONHTTPSVERIFY'] = '0'
            
            youtube_client = build('youtube', 'v3', 
                        developerKey=api_key,
                        http=http,
                        cache_discovery=False)
            
            self.logger.info("YouTube API 客戶端初始化成功")
            return youtube_client
            
        except Exception as e:
            self.logger.error(f"初始化 YouTube API 時發生錯誤: {str(e)}")
            # 如果自定義初始化失敗，嘗試標準初始化
            try:
                api_key = os.getenv('YOUTUBE_API_KEY')
                if api_key:
                    youtube_client = build('youtube', 'v3', 
                               developerKey=api_key,
                               cache_discovery=False)
                    self.logger.info("使用標準方法初始化 YouTube API 客戶端成功")
                    return youtube_client
            except Exception as e2:
                self.logger.error(f"標準 YouTube API 初始化也失敗: {str(e2)}")
            
            return None

    async def _search_youtube_with_retry(self, query: str, max_retries=3):
        """使用重試機制搜尋 YouTube，處理 SSL 錯誤"""
        for attempt in range(max_retries):
            try:
                self.logger.info(f"使用 YouTube API 搜尋: {query} (嘗試 {attempt + 1}/{max_retries})")
                
                # 確保 SSL 設定
                ssl._create_default_https_context = ssl._create_unverified_context
                os.environ['PYTHONHTTPSVERIFY'] = '0'
                
                # 如果 YouTube API 客戶端無效，嘗試重新初始化
                if not self.youtube:
                    self.youtube = self._initialize_youtube_api()
                    if not self.youtube:
                        raise Exception("無法初始化 YouTube API 客戶端")
                
                search_response = self.youtube.search().list(
                    q=query,
                    part='id,snippet',
                    maxResults=5,
                    type='video'
                ).execute()
                
                return search_response
                
            except Exception as e:
                self.logger.error(f"YouTube API 搜尋錯誤 (嘗試 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    # 等待後重試，並嘗試重新初始化 API 客戶端
                    await asyncio.sleep(1 + attempt)
                    self.youtube = self._initialize_youtube_api()
                    continue
                else:
                    raise e
        
        return None

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

    def after_playing_callback(self, guild_id, error=None):
        """建立一個當歌曲播放完畢時的回調函數
        
        這個函數解決了舊版本的回調無法正確處理特定伺服器的問題
        """
        async def _after_playing():
            if error:
                self.logger.error(f"播放時發生錯誤 (伺服器 ID: {guild_id}): {str(error)}")
            
            # 確保是非同步環境
            try:
                # 獲取特定伺服器的佇列
                queue = self.get_queue(guild_id)
                
                # 檢查佇列是否存在且語音客戶端有效
                if queue and queue.voice_client:
                    self.logger.info(f"歌曲播放完畢，檢查佇列 (伺服器 ID: {guild_id})")
                    
                    # 如果不再播放，則嘗試播放下一首
                    if not queue.voice_client.is_playing():
                        await self.play_next(guild_id)
                else:
                    self.logger.warning(f"佇列或語音客戶端無效 (伺服器 ID: {guild_id})")
            except Exception as e:
                self.logger.error(f"在處理播放完畢回調時發生錯誤: {str(e)}")

        # 返回一個同步回調函數，建立任務執行非同步處理
        def wrapper(error=None):
            asyncio.run_coroutine_threadsafe(_after_playing(), self.bot.loop)
            
        return wrapper

    async def get_audio_url(self, url: str) -> Optional[Dict[str, str]]:
        """使用 yt-dlp 獲取音訊 URL，帶有增強的錯誤處理"""
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                # 確保每次都設置不驗證 SSL
                import ssl
                import os
                ssl._create_default_https_context = ssl._create_unverified_context
                
                # 設置環境變數
                os.environ['PYTHONHTTPSVERIFY'] = '0'
                
                # 動態調整 yt-dlp 選項
                current_opts = self.ydl_opts.copy()
                
                # 如果是 YouTube URL，嘗試不同的提取器設定
                if 'youtube.com' in url or 'youtu.be' in url:
                    current_opts.update({
                        'extractor_args': {
                            'youtube': {
                                'skip': ['dash', 'hls']
                            }
                        },
                        'force_generic_extractor': False,
                    })
                
                with yt_dlp.YoutubeDL(current_opts) as ydl:
                    info = await asyncio.get_event_loop().run_in_executor(
                        None, 
                        lambda: ydl.extract_info(url, download=False)
                    )
                    if not info:
                        self.logger.warning(f"無法獲取 URL {url} 的資訊")
                        return None
                        
                    return {
                        'url': info['url'],
                        'title': info['title']
                    }
            except Exception as e:
                self.logger.error(f"獲取音訊 URL 時發生錯誤 (嘗試 {retry_count + 1}/{max_retries}): {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    # 嘗試更新 yt-dlp
                    if retry_count == 1:
                        try:
                            import subprocess
                            subprocess.run(['pip', 'install', '--upgrade', 'yt-dlp'], 
                                         capture_output=True, text=True)
                            self.logger.info("已嘗試更新 yt-dlp")
                        except:
                            pass
                    await asyncio.sleep(2)  # 增加等待時間
                    continue
                else:
                    raise Exception(f"無法獲取音訊 URL: {str(e)}")
        
        return None

    async def play_next(self, guild_id: int, ctx = None):
        """播放下一首歌曲
        
        優化的版本增加了更多診斷和錯誤處理
        """
        # 獲取伺服器的佇列
        queue = self.get_queue(guild_id)
        if not queue:
            self.logger.error(f"找不到 guild_id {guild_id} 的佇列")
            return

        # 輸出佇列狀態
        self.logger.info(f"佇列狀態 - 伺服器 {guild_id}: "
                         f"佇列長度={len(queue.queue)}, "
                         f"正在播放={queue.is_playing}, "
                         f"循環模式={queue.loop}")
            
        # 檢查語音客戶端狀態並嘗試恢復
        guild = self.bot.get_guild(guild_id)
        if not guild:
            self.logger.error(f"找不到伺服器 ID: {guild_id}")
            return
            
        # 檢查並嘗試恢復語音客戶端
        if not queue.voice_client:
            # 如果提供了 context，嘗試使用它恢復連接
            if ctx and ctx.guild.voice_client:
                queue.voice_client = ctx.guild.voice_client
                self.logger.info(f"已從 ctx 恢復語音客戶端連接 (伺服器 ID: {guild_id})")
            # 否則嘗試從 guild 恢復
            elif guild.voice_client:
                queue.voice_client = guild.voice_client
                self.logger.info(f"已從 guild 恢復語音客戶端連接 (伺服器 ID: {guild_id})")
            else:
                self.logger.error(f"無法恢復語音連接 (伺服器 ID: {guild_id})")
                if ctx:
                    await ctx.reply("與語音頻道的連接已丟失，請重新加入並使用 `/play` 指令。", ephemeral=True)
                return

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
                
                # 使用改進的回調函數，確保能夠識別特定的伺服器
                queue.voice_client.play(
                    source, 
                    after=self.after_playing_callback(guild_id)
                )
                queue.is_playing = True
                
                self.logger.info(f"開始播放音訊 (伺服器 ID: {guild_id})")
                
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
            # 使用帶重試機制的 YouTube API 搜尋
            search_response = await self._search_youtube_with_retry(query)
            
            if not search_response or not search_response.get('items'):
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
            try:
                # 先停止播放
                if queue.voice_client.is_playing():
                    queue.voice_client.stop()
                
                # 嘗試斷開連接
                await queue.voice_client.disconnect(force=True)
                self.logger.info(f"已從語音頻道斷開連接 (伺服器 ID: {ctx.guild.id})")
            except Exception as e:
                self.logger.error(f"斷開語音連接時發生錯誤: {str(e)}")
            finally:
                # 無論如何都清空佇列
                queue.clear()
                
            await ctx.reply("已停止播放並清空佇列！", ephemeral=True)
        else:
            await ctx.reply("機器人不在語音頻道中。", ephemeral=True)
            
    @commands.hybrid_command(name='leave', description='讓機器人離開語音頻道')
    async def leave_voice(self, ctx: commands.Context):
        """讓機器人離開語音頻道，但不清空佇列"""
        await ctx.defer()
        
        queue = self.get_queue(ctx.guild.id)
        guild = ctx.guild
        
        # 檢查機器人是否在語音頻道中
        if not (queue.voice_client or (guild and guild.voice_client)):
            await ctx.reply("機器人不在語音頻道中。", ephemeral=True)
            return
            
        try:
            # 停止當前播放
            voice_client = queue.voice_client or guild.voice_client
            if voice_client and voice_client.is_playing():
                voice_client.stop()
                self.logger.info(f"已停止播放 (伺服器 ID: {ctx.guild.id})")
                
            # 斷開連接
            if voice_client and voice_client.is_connected():
                await voice_client.disconnect(force=True)
                self.logger.info(f"已離開語音頻道 (伺服器 ID: {ctx.guild.id})")
            
            # 更新佇列狀態但不清空
            queue.is_playing = False
            queue.voice_client = None
            
            await ctx.reply("已離開語音頻道！佇列保留。", ephemeral=True)
        except Exception as e:
            self.logger.error(f"離開語音頻道時發生錯誤: {str(e)}")
            await ctx.reply(f"離開語音頻道時發生錯誤，請稍後再試。", ephemeral=True)
            
    @commands.hybrid_command(name='queue', description='查看當前的歌曲佇列')
    async def show_queue(self, ctx: commands.Context):
        """顯示當前的歌曲佇列"""
        await ctx.defer()
        
        queue = self.get_queue(ctx.guild.id)
        if not queue.is_playing and not queue.queue:
            await ctx.reply("目前沒有歌曲在佇列中。", ephemeral=True)
            return
            
        # 建立佇列資訊嵌入訊息
        embed = discord.Embed(
            title="🎵 歌曲佇列",
            description=queue.get_queue_info(),
            color=discord.Color.blue()
        )
        
        # 顯示循環模式狀態
        embed.add_field(
            name="循環模式", 
            value="✅ 開啟" if queue.loop else "❌ 關閉", 
            inline=True
        )
        
        # 顯示佇列長度
        embed.add_field(
            name="佇列總長", 
            value=f"{len(queue.queue)} 首歌曲", 
            inline=True
        )
        
        # 如果正在播放，顯示目前播放時間
        if queue.voice_client and queue.voice_client.is_playing():
            embed.set_footer(text=f"使用 /skip 跳過當前歌曲 | /stop 停止播放 | /leave 離開頻道")
        
        await ctx.reply(embed=embed)
        
    @tasks.loop(seconds=30)
    async def check_voice_activity(self):
        """定期檢查機器人是否在空語音頻道中，如果是則自動離開"""
        try:
            for guild in self.bot.guilds:
                # 檢查機器人是否在該伺服器的語音頻道中
                voice_client = guild.voice_client
                if not voice_client or not voice_client.is_connected():
                    continue
                    
                # 獲取佇列
                queue = self.get_queue(guild.id)
                
                # 檢查頻道是否只有機器人一人
                voice_channel = voice_client.channel
                human_members = [m for m in voice_channel.members if not m.bot]
                
                # 如果頻道中沒有人類成員，或閒置超過5分鐘，則離開
                if (not human_members) or (not voice_client.is_playing() and 
                        queue.last_updated and 
                        datetime.now() - queue.last_updated > timedelta(minutes=5)):
                    self.logger.info(f"檢測到空語音頻道或閒置超時，自動離開 (伺服器: {guild.id})")
                    
                    try:
                        # 停止播放並離開
                        if voice_client.is_playing():
                            voice_client.stop()
                        await voice_client.disconnect(force=True)
                        
                        # 更新佇列狀態
                        queue.is_playing = False
                        queue.voice_client = None
                    except Exception as e:
                        self.logger.error(f"自動離開語音頻道時發生錯誤: {str(e)}")
        except Exception as e:
            self.logger.error(f"檢查語音活動時發生錯誤: {str(e)}")
    
    @check_voice_activity.before_loop
    async def before_check_voice(self):
        """在啟動任務前等待機器人準備好"""
        await self.bot.wait_until_ready()
        
    def cog_unload(self):
        """當 Cog 被卸載時清理資源"""
        self.check_voice_activity.cancel()
        
        # 嘗試關閉所有語音連接
        for guild_id, queue in self.queues.items():
            if queue.voice_client and queue.voice_client.is_connected():
                try:
                    self.bot.loop.create_task(queue.voice_client.disconnect(force=True))
                except:
                    pass

async def setup(bot):
    await bot.add_cog(Music(bot))
