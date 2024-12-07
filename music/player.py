import discord
import yt_dlp
import asyncio
import html
from config import FFMPEG_PATH
from .queue import queues

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'ffmpeg_location': FFMPEG_PATH
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

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
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            try:
                # 獲取影片資訊
                info = await bot.loop.run_in_executor(None, lambda: ydl.extract_info(next_song['url'], download=False))
                if not info:
                    raise Exception("無法獲取影片資訊")

                # 確保我們有正確的串流 URL
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
                        print(f"播放錯誤：{error}")
                        if isinstance(error, Exception):
                            print(f"錯誤詳情：{str(error)}")
                    asyncio.run_coroutine_threadsafe(play_next(guild_id, bot), bot.loop)

                # 播放音訊
                if not queue.voice_client.is_playing():
                    queue.voice_client.play(audio_source, after=after_playing)
                    queue.is_playing = True
                    
                    if interaction:
                        title = html.unescape(info.get('title', next_song['title']))
                        embed = discord.Embed(
                            title="🎵 正在播放",
                            description=title,
                            color=discord.Color.green()
                        )
                        await interaction.channel.send(embed=embed)
                
            except Exception as e:
                print(f"影片資訊提取錯誤：{e}")
                if interaction:
                    embed = discord.Embed(
                        title="❌ 錯誤",
                        description="無法獲取影片資訊",
                        color=discord.Color.red()
                    )
                    await interaction.channel.send(embed=embed)
                await play_next(guild_id, bot, interaction)
                
    except Exception as e:
        print(f"yt-dlp 錯誤：{e}")
        if interaction:
            embed = discord.Embed(
                title="❌ 錯誤",
                description="YouTube 下載錯誤",
                color=discord.Color.red()
            )
            await interaction.channel.send(embed=embed)
        await play_next(guild_id, bot, interaction)
