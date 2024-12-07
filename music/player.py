import discord
import yt_dlp
import asyncio
import html
import re
from config import FFMPEG_PATH
from .queue import queues

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'ffmpeg_location': FFMPEG_PATH,
    'extract_flat': 'in_playlist'
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
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
            print(f"YouTube 資訊提取錯誤：{str(e)}")
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
            url = audio_formats[0]['url']

        # 創建音訊來源
        audio_source = discord.FFmpegPCMAudio(
            url,
            executable=FFMPEG_PATH,
            **FFMPEG_OPTIONS
        )

        def after_playing(error):
            if error:
                print(f"播放錯誤：{str(error)}")
            asyncio.run_coroutine_threadsafe(play_next(guild_id, bot), bot.loop)

        # 檢查並播放
        if not queue.voice_client.is_playing():
            queue.voice_client.play(audio_source, after=after_playing)
            queue.is_playing = True
            
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
        print(f"播放錯誤：{str(e)}")
        if interaction:
            embed = discord.Embed(
                title="❌ 錯誤",
                description=f"無法播放此歌曲：{str(e)}",
                color=discord.Color.red()
            )
            await interaction.channel.send(embed=embed)
        
        # 跳到下一首
        await play_next(guild_id, bot, interaction)
