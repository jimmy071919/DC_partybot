import discord
import yt_dlp
import asyncio
import html
from config import FFMPEG_PATH
from .queue import queues

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
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'ffmpeg_location': FFMPEG_PATH
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(next_song['url'], download=False)
            url = info['url']
            
            def after_playing(error):
                if error:
                    print(f"播放錯誤：{error}")
                asyncio.run_coroutine_threadsafe(play_next(guild_id, bot), bot.loop)
            
            queue.voice_client.play(discord.FFmpegPCMAudio(url, executable=FFMPEG_PATH), after=after_playing)
            queue.is_playing = True
            
            if interaction:
                title = html.unescape(next_song['title'])
                asyncio.run_coroutine_threadsafe(
                    interaction.channel.send(f"🎵 正在播放：{title}"),
                    bot.loop
                )
            
    except Exception as e:
        print(f"播放錯誤：{e}")
        await play_next(guild_id, bot, interaction)
