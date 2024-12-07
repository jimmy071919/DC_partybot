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
        'ffmpeg_location': FFMPEG_PATH,
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'no_color': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(next_song['url'], download=False)
                if not info:
                    raise Exception("無法獲取影片資訊")
                
                formats = info.get('formats', [])
                if not formats:
                    raise Exception("無法獲取音訊格式")
                
                # 選擇最佳的音訊格式
                audio_formats = [f for f in formats if f.get('acodec') != 'none']
                if not audio_formats:
                    raise Exception("找不到可用的音訊格式")
                
                best_audio = audio_formats[0]
                url = best_audio['url']
                
                def after_playing(error):
                    if error:
                        print(f"播放錯誤：{error}")
                    asyncio.run_coroutine_threadsafe(play_next(guild_id, bot), bot.loop)
                
                try:
                    queue.voice_client.play(
                        discord.FFmpegPCMAudio(
                            url,
                            executable=FFMPEG_PATH,
                            before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
                        ),
                        after=after_playing
                    )
                    queue.is_playing = True
                    
                    if interaction:
                        title = html.unescape(next_song['title'])
                        asyncio.run_coroutine_threadsafe(
                            interaction.channel.send(f"🎵 正在播放：{title}"),
                            bot.loop
                        )
                except Exception as e:
                    print(f"音訊播放錯誤：{e}")
                    if interaction:
                        asyncio.run_coroutine_threadsafe(
                            interaction.channel.send("❌ 無法播放此音訊"),
                            bot.loop
                        )
                    await play_next(guild_id, bot, interaction)
                    
            except Exception as e:
                print(f"影片資訊提取錯誤：{e}")
                if interaction:
                    asyncio.run_coroutine_threadsafe(
                        interaction.channel.send("❌ 無法獲取影片資訊"),
                        bot.loop
                    )
                await play_next(guild_id, bot, interaction)
                
    except Exception as e:
        print(f"yt-dlp 錯誤：{e}")
        if interaction:
            asyncio.run_coroutine_threadsafe(
                interaction.channel.send("❌ YouTube 下載錯誤"),
                bot.loop
            )
        await play_next(guild_id, bot, interaction)
