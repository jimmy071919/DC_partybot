import discord
import yt_dlp
import asyncio
import html
import logging
import ssl
import certifi
from config import FFMPEG_PATH
from .queue import queues

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('music_player')

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'noplaylist': True,
    'nocheckcertificate': False,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'ffmpeg_location': FFMPEG_PATH,
    'extract_flat': 'in_playlist',
    'ssl_verify': True,
    'ca_cert': certifi.where()
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -b:a 128k'
}

def get_youtube_info(url):
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        try:
            # 嘗試直接獲取資訊
            info = ydl.extract_info(url, download=False)
            if info:
                return info

            # 如果失敗，檢查是否為 YouTube 短網址
            if 'youtu.be' in url:
                video_id = url.split('/')[-1]
                new_url = f'https://www.youtube.com/watch?v={video_id}'
                info = ydl.extract_info(new_url, download=False)
                return info

            # 如果還是失敗，嘗試搜尋
            if not info:
                search_url = f'ytsearch:{url}'
                info = ydl.extract_info(search_url, download=False)
                if 'entries' in info:
                    return info['entries'][0]
                return info

        except Exception as e:
            logger.error(f"YouTube 資訊提取錯誤：{str(e)}")
            return None

async def play_next(guild_id, bot, interaction=None):
    if guild_id not in queues:
        return
    
    queue = queues[guild_id]
    
    if not queue.queue:
        queue.is_playing = False
        queue.current = None
        return
    
    next_song = queue.get_next()
    queue.current = next_song
    
    try:
        # 在執行緒池中執行 YouTube 資訊提取
        info = await bot.loop.run_in_executor(None, lambda: get_youtube_info(next_song['url']))
        
        if not info:
            raise Exception("無法獲取影片資訊")

        # 獲取音訊 URL
        if 'url' in info:
            url = info['url']
        else:
            formats = info.get('formats', [info])
            audio_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('url')]
            if not audio_formats:
                raise Exception("找不到可用的音訊格式")
            
            # 選擇最佳音質的格式
            best_format = max(audio_formats, key=lambda f: int(f.get('abr', 0)))
            url = best_format['url']
            logger.info(f"選擇的音訊格式：{best_format.get('format_id')} ({best_format.get('abr')}k)")

        # 創建音訊來源
        try:
            audio_source = discord.FFmpegPCMAudio(
                url,
                executable=FFMPEG_PATH,
                **FFMPEG_OPTIONS
            )
        except Exception as e:
            logger.error(f"創建音訊來源失敗：{str(e)}")
            raise

        def after_playing(error):
            if error:
                logger.error(f"播放錯誤：{str(error)}")
            asyncio.run_coroutine_threadsafe(play_next(guild_id, bot), bot.loop)

        # 檢查並播放
        if not queue.voice_client.is_playing():
            try:
                queue.voice_client.play(audio_source, after=after_playing)
                queue.is_playing = True
                logger.info(f"開始播放：{info.get('title')}")
                
                if interaction:
                    title = html.unescape(info.get('title', next_song['title']))
                    duration = info.get('duration_string', 'N/A')
                    
                    embed = discord.Embed(
                        title="🎵 正在播放",
                        description=f"**{title}**\n⏱️ 長度：{duration}",
                        color=discord.Color.green()
                    )
                    
                    if thumbnail := info.get('thumbnail'):
                        embed.set_thumbnail(url=thumbnail)
                    
                    await interaction.channel.send(embed=embed)
            except Exception as e:
                logger.error(f"播放音訊失敗：{str(e)}")
                raise
                
    except Exception as e:
        logger.error(f"播放錯誤：{str(e)}")
        if interaction:
            embed = discord.Embed(
                title="❌ 錯誤",
                description=f"無法播放此歌曲：{str(e)}",
                color=discord.Color.red()
            )
            await interaction.channel.send(embed=embed)
        
        # 跳到下一首
        await play_next(guild_id, bot, interaction)
