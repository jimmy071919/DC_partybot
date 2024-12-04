import discord
from discord.ext import commands, tasks
from googleapiclient.discovery import build
import yt_dlp
import random
import asyncio
from datetime import datetime, timedelta
import json
import os
import html
import requests

# YouTube API 憑證
YOUTUBE_API_KEY = "AIzaSyDYpAfzxelrrH2S2-wGUR4_D7GXFtEHTJk"

# 指定 FFmpeg 的執行檔路徑
FFMPEG_PATH = "C:\\Program Files\\ffmpeg-7.1-full_build\\bin\\ffmpeg.exe"

# 提醒的資料
reminders = {}  # 儲存提醒事項

# 檢查並載入已存在的資料
if os.path.exists('reminders.json'):
    with open('reminders.json', 'r', encoding='utf-8') as f:
        reminders = json.load(f)

# 初始化 Discord 機器人
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree  # 斜線指令專用

# 播放佇列
class MusicQueue:
    def __init__(self):
        self.queue = []
        self.current = None
        self.voice_client = None
        self.is_playing = False

    def add(self, song):
        self.queue.append(song)

    def get_next(self):
        if self.queue:
            return self.queue.pop(0)
        return None

    def clear(self):
        self.queue.clear()
        self.current = None

# 為每個伺服器建立獨立的播放佇列
queues = {}

# 播放下一首歌
async def play_next(guild_id, interaction=None):
    if guild_id not in queues:
        return
    
    queue = queues[guild_id]
    
    # 如果沒有下一首歌
    if not queue.queue:
        queue.is_playing = False
        queue.current = None
        return
    
    # 取得下一首歌
    next_song = queue.get_next()
    queue.current = next_song
    
    # 設定 yt-dlp 選項
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
            
            # 設定播放完成後的回調
            def after_playing(error):
                if error:
                    print(f"播放錯誤：{error}")
                asyncio.run_coroutine_threadsafe(play_next(guild_id), bot.loop)
            
            # 播放音樂
            queue.voice_client.play(discord.FFmpegPCMAudio(url, executable=FFMPEG_PATH), after=after_playing)
            queue.is_playing = True
            
            # 發送正在播放的訊息
            if interaction:
                title = html.unescape(next_song['title'])
                asyncio.run_coroutine_threadsafe(
                    interaction.channel.send(f"🎵 正在播放：{title}"),
                    bot.loop
                )
            
    except Exception as e:
        print(f"播放錯誤：{e}")
        await play_next(guild_id, interaction)

# 機器人啟動事件
@bot.event
async def on_ready():
    try:
        print(f"正在同步指令...")
        # 強制同步所有指令
        commands = await tree.sync()
        print(f"成功同步 {len(commands)} 個指令！")
        print(f"已登入為 {bot.user}")
        
        # 啟動定時提醒檢查
        check_reminders.start()
        
        # 列出所有已註冊的指令
        print("\n已註冊的指令：")
        for cmd in tree.get_commands():
            print(f"- /{cmd.name}: {cmd.description}")
            
    except Exception as e:
        print(f"同步指令時發生錯誤：{str(e)}")

# 搜尋 YouTube 音樂
def search_youtube(query):
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    
    # 搜尋影片
    request = youtube.search().list(
        part="snippet",
        q=query,
        type="video",
        maxResults=10  # 改為 10 個結果
    )
    response = request.execute()
    
    # 整理搜尋結果
    videos = []
    for item in response['items']:
        video = {
            "title": item['snippet']['title'],
            "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
            "channel": item['snippet']['channelTitle']
        }
        videos.append(video)
    return videos

# 加入語音頻道指令
@tree.command(name="join", description="讓機器人加入用戶所在的語音頻道")
async def join(interaction: discord.Interaction):
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

# 播放音樂指令
@tree.command(name="play", description="播放指定關鍵字的音樂")
async def play(interaction: discord.Interaction, query: str):
    # 確認使用者在語音頻道中
    if not interaction.user.voice:
        await interaction.response.send_message("請先加入語音頻道！", ephemeral=True)
        return

    # 搜尋影片
    try:
        videos = search_youtube(query)
    except Exception as e:
        await interaction.response.send_message("搜尋時發生錯誤！", ephemeral=True)
        return

    # 建立搜尋結果訊息
    embed = discord.Embed(title="YouTube 搜尋結果", color=discord.Color.blue())
    for i, video in enumerate(videos):
        embed.add_field(
            name=f"{i+1}. {html.unescape(video['title'])}", 
            value=f"頻道: {video['channel']}\n[點擊觀看]({video['url']})", 
            inline=False
        )
    
    # 建立選擇按鈕
    class SongSelectView(discord.ui.View):
        def __init__(self, videos):
            super().__init__(timeout=30.0)
            self.videos = videos
            self.selected_song = None

        @discord.ui.button(label="1", style=discord.ButtonStyle.primary)
        async def button1_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.selected_song = self.videos[0]
            self.stop()
            await self.handle_song_selection(interaction)

        @discord.ui.button(label="2", style=discord.ButtonStyle.primary)
        async def button2_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.selected_song = self.videos[1]
            self.stop()
            await self.handle_song_selection(interaction)

        @discord.ui.button(label="3", style=discord.ButtonStyle.primary)
        async def button3_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.selected_song = self.videos[2]
            self.stop()
            await self.handle_song_selection(interaction)

        @discord.ui.button(label="4", style=discord.ButtonStyle.primary)
        async def button4_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.selected_song = self.videos[3]
            self.stop()
            await self.handle_song_selection(interaction)

        @discord.ui.button(label="5", style=discord.ButtonStyle.primary)
        async def button5_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.selected_song = self.videos[4]
            self.stop()
            await self.handle_song_selection(interaction)
        
        @discord.ui.button(label="6", style=discord.ButtonStyle.primary)
        async def button6_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.selected_song = self.videos[5]
            self.stop()
            await self.handle_song_selection(interaction)
        
        @discord.ui.button(label="7", style=discord.ButtonStyle.primary)
        async def button7_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.selected_song = self.videos[6]
            self.stop()
            await self.handle_song_selection(interaction)

        @discord.ui.button(label="8", style=discord.ButtonStyle.primary)
        async def button8_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.selected_song = self.videos[7]
            self.stop()
            await self.handle_song_selection(interaction)
        
        @discord.ui.button(label="9", style=discord.ButtonStyle.primary)
        async def button9_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.selected_song = self.videos[8]
            self.stop()
            await self.handle_song_selection(interaction)
        
        @discord.ui.button(label="10", style=discord.ButtonStyle.primary)
        async def button10_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.selected_song = self.videos[9]
            self.stop()
            await self.handle_song_selection(interaction)

        async def handle_song_selection(self, interaction: discord.Interaction):
            # 初始化該伺服器的播放佇列
            if interaction.guild_id not in queues:
                queues[interaction.guild_id] = MusicQueue()
            
            queue = queues[interaction.guild_id]
            
            # 準備歌曲資訊
            song = {
                "title": html.unescape(self.selected_song["title"]),
                "url": self.selected_song["url"]
            }
            
            # 如果機器人不在語音頻道，就加入
            if not queue.voice_client or not queue.voice_client.is_connected():
                try:
                    queue.voice_client = await interaction.user.voice.channel.connect()
                except discord.ClientException:
                    queue.voice_client = interaction.guild.voice_client
            
            # 將歌曲加入佇列
            queue.add(song)
            
            # 如果沒有正在播放的音樂，就開始播放
            if not queue.is_playing:
                await interaction.response.send_message(f"🎵 即將播放：{song['title']}")
                await play_next(interaction.guild_id, interaction)
            else:
                await interaction.response.send_message(f"🎵 已加入播放佇列：{song['title']}")

        async def on_timeout(self):
            # 處理超時情況
            for child in self.children:
                child.disabled = True

    # 發送包含按鈕的訊息
    view = SongSelectView(videos)
    await interaction.response.send_message(embed=embed, view=view)

# 顯示播放佇列指令
@tree.command(name="queue", description="顯示目前的播放佇列")
async def show_queue(interaction: discord.Interaction):
    if interaction.guild_id not in queues:
        await interaction.response.send_message("播放佇列是空的！", ephemeral=True)
        return
    
    queue = queues[interaction.guild_id]
    
    if not queue.current and not queue.queue:
        await interaction.response.send_message("播放佇列是空的！", ephemeral=True)
        return
    
    # 建立播放佇列訊息
    embed = discord.Embed(
        title="🎵 播放佇列",
        color=discord.Color.blue()
    )
    
    # 顯示目前播放的歌曲
    if queue.current:
        embed.add_field(
            name="正在播放",
            value=f"🎵 {html.unescape(queue.current['title'])}",
            inline=False
        )
    
    # 顯示佇列中的歌曲
    if queue.queue:
        queue_text = "\n".join([f"{i+1}. {html.unescape(song['title'])}" for i, song in enumerate(queue.queue)])
        embed.add_field(
            name="即將播放",
            value=queue_text,
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

# 跳過當前歌曲指令
@tree.command(name="skip", description="跳過目前播放的歌曲")
async def skip(interaction: discord.Interaction):
    if interaction.guild_id not in queues:
        await interaction.response.send_message("目前沒有正在播放的音樂！", ephemeral=True)
        return
    
    queue = queues[interaction.guild_id]
    
    if not queue.is_playing:
        await interaction.response.send_message("目前沒有正在播放的音樂！", ephemeral=True)
        return
    
    # 停止目前的歌曲，會自動播放下一首
    queue.voice_client.stop()
    await interaction.response.send_message("⏭️ 已跳過當前歌曲")

# 清除播放佇列指令
@tree.command(name="clear_queue", description="清除播放佇列")
async def clear_queue(interaction: discord.Interaction):
    if interaction.guild_id not in queues:
        await interaction.response.send_message("播放佇列已經是空的！", ephemeral=True)
        return
    
    queue = queues[interaction.guild_id]
    queue.clear()
    
    if queue.voice_client and queue.voice_client.is_playing():
        queue.voice_client.stop()
    
    await interaction.response.send_message("🗑️ 已清除播放佇列")

# 暫停音樂指令
@tree.command(name="pause", description="暫停播放的音樂")
async def pause(interaction: discord.Interaction):
    if interaction.guild_id not in queues:
        await interaction.response.send_message("目前沒有正在播放的音樂！", ephemeral=True)
        return
    
    queue = queues[interaction.guild_id]
    
    if not queue.is_playing:
        await interaction.response.send_message("目前沒有正在播放的音樂！", ephemeral=True)
        return
    
    queue.voice_client.pause()
    await interaction.response.send_message("音樂已暫停！")

# 恢復音樂指令
@tree.command(name="resume", description="繼續播放已暫停的音樂")
async def resume(interaction: discord.Interaction):
    if interaction.guild_id not in queues:
        await interaction.response.send_message("目前沒有正在播放的音樂！", ephemeral=True)
        return
    
    queue = queues[interaction.guild_id]
    
    if not queue.is_playing:
        await interaction.response.send_message("目前沒有正在播放的音樂！", ephemeral=True)
        return
    
    queue.voice_client.resume()
    await interaction.response.send_message("音樂已繼續播放！")

# 停止音樂指令
@tree.command(name="stop", description="停止播放的音樂")
async def stop(interaction: discord.Interaction):
    if interaction.guild_id not in queues:
        await interaction.response.send_message("目前沒有正在播放的音樂！", ephemeral=True)
        return
    
    queue = queues[interaction.guild_id]
    
    if not queue.is_playing:
        await interaction.response.send_message("目前沒有正在播放的音樂！", ephemeral=True)
        return
    
    queue.voice_client.stop()
    await interaction.response.send_message("音樂已停止！")

# 離開語音頻道指令
@tree.command(name="leave", description="讓機器人離開語音頻道")
async def leave(interaction: discord.Interaction):
    if interaction.guild_id not in queues:
        await interaction.response.send_message("機器人不在任何語音頻道內！", ephemeral=True)
        return
    
    queue = queues[interaction.guild_id]
    
    if queue.voice_client:
        await queue.voice_client.disconnect()
        await interaction.response.send_message("機器人已離開語音頻道！")
    else:
        await interaction.response.send_message("機器人不在任何語音頻道內！", ephemeral=True)

# 隨機抽人指令
@tree.command(name="random", description="從語音頻道中隨機抽選一個人")
async def random_pick(interaction: discord.Interaction):
    # 檢查指令發送者是否在語音頻道中
    if not interaction.user.voice:
        await interaction.response.send_message("你必須先加入語音頻道！", ephemeral=True)
        return
    
    # 獲取語音頻道中的所有成員
    voice_channel = interaction.user.voice.channel
    members = [member for member in voice_channel.members if not member.bot]  # 排除機器人
    
    if not members:
        await interaction.response.send_message("語音頻道中沒有其他成員！", ephemeral=True)
        return
    
    # 隨機選擇一個成員
    chosen_one = random.choice(members)
    
    # 創建一個漂亮的 embed 訊息
    embed = discord.Embed(
        title="🎲 隨機抽選結果",
        description=f"恭喜 **{chosen_one.display_name}** 被選中！",
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=chosen_one.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)

# 擲骰子指令
@tree.command(name="roll", description="擲骰子 (預設 1-100)")
async def roll(interaction: discord.Interaction, max_number: int = 100):
    if max_number < 1:
        await interaction.response.send_message("請輸入大於 0 的數字！", ephemeral=True)
        return
    
    result = random.randint(1, max_number)
    await interaction.response.send_message(f"🎲 {interaction.user.display_name} 擲出了 **{result}** 點！")

# 投票指令
@tree.command(name="poll", description="建立投票")
async def poll(interaction: discord.Interaction, question: str, options: str):
    # 分割選項
    option_list = [opt.strip() for opt in options.split(',')]
    
    # 檢查選項數量
    if len(option_list) < 2:
        await interaction.response.send_message("至少需要2個選項！", ephemeral=True)
        return
    elif len(option_list) > 20:
        await interaction.response.send_message("最多只能有20個選項！", ephemeral=True)
        return
    
    # 建立投票訊息
    embed = discord.Embed(
        title=question,
        description="請點擊下方表情符號來投票！",
        color=discord.Color.blue()
    )
    
    # 添加選項到 embed
    for i, option in enumerate(option_list):
        embed.add_field(
            name=f"{i+1}. {option}", 
            value="", 
            inline=False
        )
    
    # 發送投票訊息
    message = await interaction.response.send_message(embed=embed)
    
    # 取得已發送的訊息
    message = await interaction.original_response()
    
    # 添加數字反應（使用 0-9 和 a-j 的 regional indicators）
    for i in range(len(option_list)):
        if i < 10:
            await message.add_reaction(f"{i+1}\u20e3")  # 使用數字 + 組合字元
        else:
            # 10以後使用字母
            await message.add_reaction(chr(0x1F1E6 + (i-10)))  # 使用區域指示符號字母

# 清除訊息指令
@tree.command(name="clear", description="清除指定數量的訊息")
async def clear(interaction: discord.Interaction, amount: int = 5):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("你沒有權限執行此指令！", ephemeral=True)
        return
    
    if amount < 1 or amount > 100:
        await interaction.response.send_message("請輸入 1-100 之間的數字！", ephemeral=True)
        return
    
    await interaction.response.defer()
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"已清除 {len(deleted)} 則訊息！", ephemeral=True)

# 用戶資訊指令
@tree.command(name="userinfo", description="顯示用戶資訊")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    # 如果沒有指定成員，就顯示指令使用者的資訊
    if member is None:
        member = interaction.user
    
    # 建立資訊 embed
    embed = discord.Embed(
        title=f"👤 {member.display_name} 的資訊",
        color=member.color
    )
    
    # 添加用戶資訊
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="用戶 ID", value=member.id, inline=True)
    embed.add_field(name="加入時間", value=member.joined_at.strftime("%Y/%m/%d"), inline=True)
    embed.add_field(name="帳號建立時間", value=member.created_at.strftime("%Y/%m/%d"), inline=True)
    embed.add_field(name="身分組", value=" ".join([role.mention for role in member.roles[1:]]) or "無", inline=False)
    
    await interaction.response.send_message(embed=embed)

# 定時提醒相關功能
@tasks.loop(seconds=60)  # 每分鐘檢查一次
async def check_reminders():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    if current_time in reminders:
        for reminder in reminders[current_time]:
            channel = bot.get_channel(reminder["channel_id"])
            if channel:
                await channel.send(f"<@{reminder['user_id']}> 提醒：{reminder['message']}")
        del reminders[current_time]
        # 儲存更新後的提醒
        with open('reminders.json', 'w', encoding='utf-8') as f:
            json.dump(reminders, f, ensure_ascii=False, indent=2)

@tree.command(name="remind", description="設定提醒")
async def set_reminder(interaction: discord.Interaction, minutes: int, message: str):
    if minutes <= 0:
        await interaction.response.send_message("請輸入大於 0 的分鐘數！", ephemeral=True)
        return
    
    # 計算提醒時間
    remind_time = datetime.now() + timedelta(minutes=minutes)
    time_str = remind_time.strftime("%Y-%m-%d %H:%M")
    
    # 儲存提醒
    if time_str not in reminders:
        reminders[time_str] = []
    
    reminders[time_str].append({
        "user_id": interaction.user.id,
        "channel_id": interaction.channel_id,
        "message": message
    })
    
    # 儲存到文件
    with open('reminders.json', 'w', encoding='utf-8') as f:
        json.dump(reminders, f, ensure_ascii=False, indent=2)
    
    await interaction.response.send_message(
        f"已設定提醒！\n時間：{time_str}\n內容：{message}",
        ephemeral=True
    )

# Tenor API 設定
TENOR_API_KEY = "YOUR_TENOR_API_KEY"  # 請替換為你的 Tenor API 金鑰
TENOR_API_URL = "https://tenor.googleapis.com/v2/search"

# 讀取表情符號數據
def load_emoji_data():
    try:
        with open('emoji_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"keywords": {}, "gif_categories": {}}

# 獲取隨機 GIF
async def get_random_gif(category):
    params = {
        "q": category,
        "key": TENOR_API_KEY,
        "client_key": "discord_bot",
        "limit": 10,
        "media_filter": "gif"
    }
    
    try:
        response = requests.get(TENOR_API_URL, params=params)
        data = response.json()
        if "results" in data and data["results"]:
            gif = random.choice(data["results"])
            return gif["media_formats"]["gif"]["url"]
    except Exception as e:
        print(f"獲取 GIF 時發生錯誤：{e}")
    return None

# 獲取推薦表情符號
def get_recommended_emojis(text):
    emoji_data = load_emoji_data()
    recommended = []
    
    # 檢查文字中是否包含關鍵字
    for keyword, emojis in emoji_data["keywords"].items():
        if keyword in text:
            recommended.extend(random.sample(emojis, min(3, len(emojis))))
    
    return list(set(recommended))

# 表情推薦指令
@tree.command(name="emoji", description="獲取表情符號推薦")
async def recommend_emoji(interaction: discord.Interaction, text: str):
    emojis = get_recommended_emojis(text)
    
    if not emojis:
        await interaction.response.send_message("找不到相關的表情符號推薦 😅", ephemeral=True)
        return
    
    await interaction.response.send_message(
        f"推薦的表情符號：{''.join(emojis)}",
        ephemeral=True
    )

# 派對 GIF 指令
@tree.command(name="party_gif", description="獲取隨機派對相關 GIF")
async def party_gif(interaction: discord.Interaction, category: str = "party"):
    emoji_data = load_emoji_data()
    
    # 檢查類別是否有效
    if category not in emoji_data["gif_categories"]:
        categories = ", ".join(emoji_data["gif_categories"].keys())
        await interaction.response.send_message(
            f"無效的類別！可用類別：{categories}",
            ephemeral=True
        )
        return
    
    # 隨機選擇一個搜尋關鍵字
    search_term = random.choice(emoji_data["gif_categories"][category])
    
    # 發送等待訊息
    await interaction.response.defer()
    
    # 獲取 GIF
    gif_url = await get_random_gif(search_term)
    
    if gif_url:
        await interaction.followup.send(gif_url)
    else:
        await interaction.followup.send("抱歉，無法獲取 GIF 😅", ephemeral=True)

# 監聽訊息事件
@bot.event
async def on_message(message):
    # 忽略機器人自己的訊息
    if message.author == bot.user:
        return
    
    # 處理指令
    await bot.process_commands(message)
    
    # 檢查是否需要推薦表情符號
    emojis = get_recommended_emojis(message.content)
    if emojis:
        # 隨機決定是否回應（避免太頻繁）
        if random.random() < 0.3:  # 30% 機率回應
            await message.add_reaction(random.choice(emojis))

# 啟動機器人
bot.run("MTMxMjA0MzQ2NjAxMTk2NzUyMA.GGIKUu.3rJhLFuWLvkhaXwugQdakJi9RcrindZpXuBjPM")