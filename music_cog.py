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
        
        # 從環境變數獲取 cookies 內容
        cookies_content = os.getenv('YOUTUBE_COOKIES')
        cookies_path = None
        
        if cookies_content:
            try:
                # 解碼 base64 內容
                decoded_cookies = base64.b64decode(cookies_content).decode('utf-8')
                
                # 確保 cookies 內容是正確的格式
                if not decoded_cookies.startswith('# Netscape HTTP Cookie File'):
                    self.logger.warning("Cookies 內容格式不正確，添加標頭")
                    decoded_cookies = "# Netscape HTTP Cookie File\n# https://curl.haxx.se/rfc/cookie_spec.html\n# This is a generated file!  Do not edit.\n\n" + decoded_cookies
                
                # 創建臨時文件
                temp_dir = tempfile.gettempdir()
                cookies_path = os.path.join(temp_dir, 'youtube.cookies')
                
                # 寫入 cookies 內容
                with open(cookies_path, 'w', encoding='utf-8') as f:
                    f.write(decoded_cookies)
                
                self.logger.info(f"已創建臨時 cookies 文件: {cookies_path}")
                
                # 確保文件權限正確
                try:
                    os.chmod(cookies_path, 0o644)
                    self.logger.info("已設置 cookies 文件權限")
                except Exception as e:
                    self.logger.warning(f"設置 cookies 文件權限時發生錯誤: {str(e)}")
                    
                # 驗證 cookies 文件
                try:
                    with open(cookies_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        self.logger.info(f"Cookies 文件大小: {len(content)} 字節")
                        if len(content.strip()) == 0:
                            self.logger.error("Cookies 文件為空")
                except Exception as e:
                    self.logger.error(f"驗證 cookies 文件時發生錯誤: {str(e)}")
                    
            except Exception as e:
                self.logger.error(f"處理 cookies 時發生錯誤: {str(e)}")
                if cookies_path and os.path.exists(cookies_path):
                    try:
                        os.remove(cookies_path)
                        self.logger.info("已刪除無效的 cookies 文件")
                    except Exception as e:
                        self.logger.error(f"刪除無效的 cookies 文件時發生錯誤: {str(e)}")
        else:
            self.logger.warning("環境變數中未找到 YOUTUBE_COOKIES")
        
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
            'extract_flat': False,
            'force_generic_extractor': False,
            'youtube_include_dash_manifest': False,
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'no_color': True,
            'geo_bypass': True,
            'socket_timeout': 30,  # 增加超時時間
            'retries': 10,  # 增加重試次數
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                    'player_skip': ['js', 'configs', 'webpage']
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-Dest': 'document'
            }
        }
        
        # 如果存在 cookies 文件，則添加到選項中
        if cookies_path and os.path.exists(cookies_path):
            self.YDL_OPTIONS['cookies'] = cookies_path
            self.logger.info(f"已將 cookies 文件添加到 yt-dlp 選項中: {cookies_path}")
            
            # 驗證 cookies 文件內容
            try:
                with open(cookies_path, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    self.logger.info(f"Cookies 文件首行: {first_line}")
                    if not first_line.startswith('# Netscape HTTP Cookie File'):
                        self.logger.warning("Cookies 文件格式可能不正確")
            except Exception as e:
                self.logger.error(f"讀取 cookies 文件時發生錯誤: {str(e)}")
        
        # 移除 cookiesfrombrowser 選項
        if 'cookiesfrombrowser' in self.YDL_OPTIONS:
            del self.YDL_OPTIONS['cookiesfrombrowser']

    def get_queue(self, guild_id: int) -> MusicQueue:
        """獲取或創建伺服器的音樂佇列"""
        if guild_id not in self.queues:
            self.queues[guild_id] = MusicQueue()
        return self.queues[guild_id]

    async def ensure_voice_connected(self, interaction: discord.Interaction, max_retries: int = 3) -> bool:
        """確保語音連接成功建立"""
        retry_count = 0
        while retry_count < max_retries:
            try:
                if not interaction.guild.voice_client:
                    self.logger.info(f"嘗試連接語音頻道 (嘗試 {retry_count + 1}/{max_retries})")
                    voice_client = await interaction.user.voice.channel.connect()
                    # 等待確保連接完全建立
                    await asyncio.sleep(1)
                    if voice_client and voice_client.is_connected():
                        self.logger.info("語音連接成功建立")
                        # 更新佇列中的語音客戶端
                        queue = self.get_queue(interaction.guild.id)
                        queue.voice_client = voice_client
                        return True
                else:
                    if interaction.guild.voice_client.is_connected():
                        # 更新佇列中的語音客戶端
                        queue = self.get_queue(interaction.guild.id)
                        queue.voice_client = interaction.guild.voice_client
                        return True
                    else:
                        await interaction.guild.voice_client.disconnect(force=True)
                        continue

            except Exception as e:
                self.logger.error(f"語音連接失敗 (嘗試 {retry_count + 1}/{max_retries}): {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    await asyncio.sleep(1)  # 等待一秒後重試
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

        if not queue.voice_client:
            self.logger.error("沒有語音客戶端連接")
            if interaction:
                await interaction.followup.send("錯誤：沒有語音客戶端連接", ephemeral=True)
            return

        if not queue.voice_client.is_connected():
            self.logger.error("語音客戶端未連接")
            if interaction:
                await interaction.followup.send("錯誤：語音客戶端未連接", ephemeral=True)
            # 嘗試重新連接
            if interaction and interaction.user.voice:
                if await self.ensure_voice_connected(interaction):
                    self.logger.info("已重新建立語音連接")
                else:
                    return
            else:
                return

        if not queue.queue and not queue.loop:
            self.logger.info("佇列為空且未開啟循環播放")
            queue.is_playing = False
            queue.current = None
            if interaction:
                await interaction.followup.send("播放佇列已空", ephemeral=True)
            return
        
        next_song = queue.get_next()
        if not next_song:
            self.logger.error("無法獲取下一首歌曲")
            if interaction:
                await interaction.followup.send("錯誤：無法獲取下一首歌曲", ephemeral=True)
            return

        self.logger.info(f"準備播放: {next_song.get('title', 'Unknown Title')} ({next_song.get('url', 'No URL')})")

        try:
            # 使用 yt-dlp 獲取音訊 URL
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,  # 需要完整提取
                'skip_download': True,
                'force_generic_extractor': False,
                'ignoreerrors': True,
                'no_color': True,
                'geo_bypass': True,
                'socket_timeout': 30,
                'retries': 10,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Sec-Fetch-Mode': 'navigate',
                    'Origin': 'https://www.youtube.com',
                    'Referer': 'https://www.youtube.com/'
                }
            }

            # 如果有 cookies，添加到選項中
            cookies = os.getenv('YOUTUBE_COOKIES')
            if cookies:
                self.logger.info("從環境變數讀取 cookies")
                try:
                    # 將 base64 編碼的 cookies 解碼並寫入臨時文件
                    cookies_content = base64.b64decode(cookies).decode('utf-8')
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                        f.write(cookies_content)
                        cookies_path = f.name
                    self.logger.info(f"已將 cookies 寫入臨時文件: {cookies_path}")
                    ydl_opts['cookies'] = cookies_path
                except Exception as e:
                    self.logger.error(f"處理 cookies 時發生錯誤: {str(e)}")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.logger.info("開始提取影片資訊...")
                info = ydl.extract_info(next_song['url'], download=False)
                
                if not info:
                    raise Exception("無法獲取影片資訊")

                # 清理臨時 cookies 文件
                if 'cookies_path' in locals():
                    try:
                        os.unlink(cookies_path)
                        self.logger.info("已刪除臨時 cookies 文件")
                    except Exception as e:
                        self.logger.error(f"刪除臨時 cookies 文件時發生錯誤: {str(e)}")

                # 獲取最佳音訊格式的 URL
                formats = info.get('formats', [])
                if not formats:
                    raise Exception("沒有可用的音訊格式")

                # 優先選擇音訊格式
                audio_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
                if audio_formats:
                    format_url = audio_formats[0]['url']
                else:
                    format_url = formats[0]['url']  # 如果沒有純音訊格式，使用第一個可用格式

                self.logger.info("成功獲取音訊 URL")

                def after_playing(error):
                    if error:
                        self.logger.error(f"播放時發生錯誤: {str(error)}")
                    asyncio.run_coroutine_threadsafe(
                        self.play_next(guild_id), 
                        self.bot.loop
                    )

                try:
                    # 嘗試播放音訊
                    queue.voice_client.play(
                        discord.FFmpegPCMAudio(
                            format_url,
                            executable='ffmpeg',
                            before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
                        ),
                        after=after_playing
                    )
                    
                    # 設置音量
                    queue.voice_client.source = discord.PCMVolumeTransformer(
                        queue.voice_client.source,
                        volume=queue.volume
                    )
                    
                    queue.is_playing = True
                    queue.current = next_song
                    self.logger.info("開始播放音樂")

                    # 發送播放通知
                    if interaction and interaction.channel:
                        embed = discord.Embed(
                            title="🎵 正在播放",
                            description=info.get('title', next_song['title']),
                            color=discord.Color.green()
                        )
                        embed.add_field(
                            name="長度",
                            value=info.get('duration_string', 'N/A')
                        )
                        embed.add_field(
                            name="請求者",
                            value=next_song.get('requester', 'Unknown')
                        )
                        await interaction.followup.send(embed=embed)
                        self.logger.info(f"已發送播放通知: {info.get('title', next_song['title'])}")

                except Exception as e:
                    self.logger.error(f"播放音訊時發生錯誤: {str(e)}")
                    if interaction:
                        await interaction.followup.send(f"播放時發生錯誤: {str(e)}", ephemeral=True)
                    raise

        except Exception as e:
            self.logger.error(f"處理下一首歌曲時發生錯誤: {str(e)}")
            if interaction:
                await interaction.followup.send(f"錯誤: {str(e)}", ephemeral=True)
            # 嘗試播放下一首
            await self.play_next(guild_id, interaction)

    async def search_youtube(self, query: str) -> List[Dict]:
        """搜尋 YouTube 影片"""
        try:
            # 首先嘗試使用 YouTube Data API 搜尋
            youtube = build('youtube', 'v3', developerKey=os.getenv('YOUTUBE_API_KEY'))
            
            # 執行搜尋
            search_response = youtube.search().list(
                q=query,
                part='id,snippet',
                maxResults=10,
                type='video'
            ).execute()

            videos = []
            for item in search_response.get('items', []):
                if item['id']['kind'] == 'youtube#video':
                    video_id = item['id']['videoId']
                    title = item['snippet']['title']
                    url = f"https://www.youtube.com/watch?v={video_id}"
                    videos.append({
                        'url': url,
                        'title': title,
                        'duration': 'N/A'  # YouTube API v3 不直接提供時長
                    })

            self.logger.info(f"使用 YouTube API 搜尋到 {len(videos)} 個影片")
            return videos

        except HttpError as e:
            self.logger.error(f"YouTube API 搜尋失敗: {str(e)}")
            
            # 如果 API 搜尋失敗，回退到 yt-dlp
            self.logger.info("回退到 yt-dlp 搜尋...")
            
            # 使用修改後的 yt-dlp 選項進行搜尋
            search_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'skip_download': True,
                'force_generic_extractor': True,
                'ignoreerrors': True,
                'no_color': True,
                'geo_bypass': True,
                'socket_timeout': 30,
                'retries': 10,
                'extractor_args': {
                    'youtube': {
                        'skip': ['dash', 'hls'],
                        'player_skip': ['js', 'configs', 'webpage']
                    }
                },
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-Dest': 'document',
                    'Origin': 'https://www.youtube.com',
                    'Referer': 'https://www.youtube.com/'
                }
            }

            # 如果有 cookies，添加到搜尋選項中
            if 'cookies' in self.YDL_OPTIONS:
                search_opts['cookies'] = self.YDL_OPTIONS['cookies']

            with yt_dlp.YoutubeDL(search_opts) as ydl:
                try:
                    self.logger.info("使用的 yt-dlp 選項: {search_opts}")
                    results = ydl.extract_info(f"ytsearch{10}:{query}", download=False)
                    
                    if not results:
                        self.logger.error("搜尋結果為空")
                        return []

                    videos = []
                    for entry in results['entries']:
                        if entry:
                            videos.append({
                                'url': f"https://www.youtube.com/watch?v={entry['id']}",
                                'title': entry.get('title', 'Unknown'),
                                'duration': entry.get('duration_string', 'N/A')
                            })

                    self.logger.info(f"搜尋結果: {len(videos)} 個影片")
                    return videos

                except Exception as e:
                    self.logger.error(f"yt-dlp 搜尋失敗: {str(e)}")
                    return []

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

            # 獲取或創建音樂佇列
            queue = self.get_queue(interaction.guild.id)
            
            # 搜索視頻
            try:
                videos = await self.search_youtube(query)
                if not videos:
                    await interaction.followup.send("找不到相關影片！", ephemeral=True)
                    return
                    
                video = videos[0]  # 使用第一個搜索結果
                video['requester'] = interaction.user.display_name
                
            except Exception as e:
                self.logger.error(f"搜索時發生錯誤: {str(e)}")
                await interaction.followup.send(f"搜索時發生錯誤：{str(e)}", ephemeral=True)
                return

            # 添加到佇列
            queue.queue.append(video)
            
            # 如果沒有正在播放，則開始播放
            if not queue.is_playing:
                await self.play_next(interaction.guild.id, interaction)
            else:
                # 如果已經在播放，則發送已加入佇列的消息
                embed = discord.Embed(
                    title="🎵 已加入播放佇列",
                    description=video['title'],
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="請求者",
                    value=video['requester']
                )
                await interaction.followup.send(embed=embed)

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
