import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import json
import os
from datetime import datetime, timedelta
from config import REMINDERS_DATA_PATH, DATA_DIR
import logging
from pathlib import Path

class Utils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tree = bot.tree
        self.reminders = {}
        self.logger = logging.getLogger(__name__)
        self.load_reminders()

    def cog_load(self):
        """當 Cog 被載入時執行"""
        self.check_reminders.start()
        self.logger.info("Utils Cog 已載入")

    def cog_unload(self):
        """當 Cog 被卸載時執行"""
        self.check_reminders.cancel()
        self.logger.info("Utils Cog 已卸載")

    def load_reminders(self):
        """載入提醒事項"""
        try:
            # 確保資料目錄存在
            os.makedirs(DATA_DIR, exist_ok=True)
            
            # 如果檔案不存在，創建一個空的提醒資料檔
            if not Path(REMINDERS_DATA_PATH).exists():
                with open(REMINDERS_DATA_PATH, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
                self.reminders = {}
                self.logger.info(f"已建立新的提醒事項檔案：{REMINDERS_DATA_PATH}")
                return
                
            # 嘗試讀取現有的提醒事項
            with open(REMINDERS_DATA_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # 過濾掉過期的提醒
                current_time = datetime.now()
                filtered_data = {}
                
                for time_str, reminders in data.items():
                    try:
                        reminder_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
                        if reminder_time > current_time:
                            filtered_data[time_str] = reminders
                    except ValueError:
                        # 如果時間格式無效，保留該條目以避免丟失數據
                        filtered_data[time_str] = reminders
                
                self.reminders = filtered_data
                
                # 如果過濾掉了部分提醒，重新儲存
                if len(data) != len(filtered_data):
                    with open(REMINDERS_DATA_PATH, 'w', encoding='utf-8') as f:
                        json.dump(filtered_data, f, ensure_ascii=False, indent=2)
                    
                self.logger.info(f"已載入 {len(filtered_data)} 個有效提醒事項")
                
        except FileNotFoundError:
            self.logger.warning(f"找不到提醒事項檔案：{REMINDERS_DATA_PATH}")
            self.reminders = {}
        except json.JSONDecodeError:
            self.logger.error("提醒事項檔案格式錯誤，將建立新檔案")
            self.reminders = {}
            # 備份錯誤的檔案
            if Path(REMINDERS_DATA_PATH).exists():
                backup_path = f"{REMINDERS_DATA_PATH}.bak"
                Path(REMINDERS_DATA_PATH).rename(backup_path)
                self.logger.info(f"已將錯誤檔案備份為：{backup_path}")
            # 建立新的空檔案
            with open(REMINDERS_DATA_PATH, 'w', encoding='utf-8') as f:
                json.dump({}, f)

    def save_reminders(self):
        """儲存提醒事項"""
        try:
            # 確保資料目錄存在
            os.makedirs(os.path.dirname(REMINDERS_DATA_PATH), exist_ok=True)
            
            with open(REMINDERS_DATA_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.reminders, f, ensure_ascii=False, indent=2)
            self.logger.debug("提醒事項已儲存")
        except Exception as e:
            self.logger.error(f"儲存提醒事項時發生錯誤：{str(e)}")
            
            # 嘗試建立臨時備份
            try:
                temp_path = f"{REMINDERS_DATA_PATH}.tmp"
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(self.reminders, f, ensure_ascii=False, indent=2)
                self.logger.info(f"已建立臨時備份：{temp_path}")
            except:
                self.logger.error("無法建立提醒事項的臨時備份")

    @tasks.loop(seconds=30)
    async def check_reminders(self):
        """檢查提醒事項 - 每30秒執行一次以提高精確度"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            if current_time in self.reminders:
                self.logger.info(f"發現 {len(self.reminders[current_time])} 個待處理提醒")
                
                for reminder in self.reminders[current_time]:
                    try:
                        # 獲取頻道和用戶
                        channel = self.bot.get_channel(reminder["channel_id"])
                        user_id = reminder["user_id"]
                        
                        if channel:
                            # 創建提醒嵌入式訊息
                            embed = discord.Embed(
                                title="⏰ 提醒時間到！",
                                description=reminder['message'],
                                color=discord.Color.gold(),
                                timestamp=datetime.now()
                            )
                            
                            # 嘗試獲取用戶資訊以添加頭像
                            try:
                                user = await self.bot.fetch_user(user_id)
                                embed.set_author(
                                    name=f"{user.display_name} 的提醒",
                                    icon_url=user.display_avatar.url
                                )
                            except:
                                # 如果無法獲取用戶資訊，使用簡單的提及
                                pass
                                
                            # 發送提醒
                            await channel.send(
                                content=f"<@{user_id}>",
                                embed=embed
                            )
                            self.logger.info(f"已發送提醒給用戶 {user_id}")
                        else:
                            self.logger.warning(f"找不到頻道：{reminder['channel_id']}")
                    except Exception as e:
                        self.logger.error(f"發送提醒時發生錯誤：{str(e)}")
                
                # 完成後從列表中移除
                del self.reminders[current_time]
                self.save_reminders()
                
        except Exception as e:
            self.logger.error(f"檢查提醒事項時發生錯誤：{str(e)}")

    @app_commands.command(name="random", description="從語音頻道中隨機抽選一個人")
    async def random_pick(self, interaction: discord.Interaction):
        """從語音頻道中隨機抽選一個人"""
        if not interaction.user.voice:
            await interaction.response.send_message(
                "你必須先加入語音頻道！",
                ephemeral=True
            )
            return
        
        voice_channel = interaction.user.voice.channel
        members = [member for member in voice_channel.members if not member.bot]
        
        if not members:
            await interaction.response.send_message(
                "語音頻道中沒有其他成員！",
                ephemeral=True
            )
            return
        
        chosen_one = random.choice(members)
        
        embed = discord.Embed(
            title="🎲 隨機抽選結果",
            description=f"恭喜 **{chosen_one.display_name}** 被選中！",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=chosen_one.display_avatar.url)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="dice_roll", description="擲骰子 (預設 1-100)")
    async def roll(self, interaction: discord.Interaction, max_number: int = 100):
        """擲骰子"""
        if max_number < 1:
            await interaction.response.send_message(
                "請輸入大於 0 的數字！",
                ephemeral=True
            )
            return
        
        result = random.randint(1, max_number)
        await interaction.response.send_message(
            f"🎲 {interaction.user.display_name} 擲出了 **{result}** 點！"
        )

    @app_commands.command(name="poll", description="建立投票")
    async def poll(self, interaction: discord.Interaction, question: str, options: str):
        """建立投票"""
        option_list = [opt.strip() for opt in options.split(',')]
        
        if len(option_list) < 2:
            await interaction.response.send_message(
                "至少需要2個選項！",
                ephemeral=True
            )
            return
        elif len(option_list) > 20:
            await interaction.response.send_message(
                "最多只能有20個選項！",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=question,
            description="請點擊下方表情符號來投票！",
            color=discord.Color.blue()
        )
        
        for i, option in enumerate(option_list):
            embed.add_field(
                name=f"{i+1}. {option}", 
                value="", 
                inline=False
            )
        
        message = await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()
        
        for i in range(len(option_list)):
            if i < 10:
                await message.add_reaction(f"{i+1}\u20e3")
            else:
                await message.add_reaction(chr(0x1F1E6 + (i-10)))

    @app_commands.command(name="clear", description="清除指定數量的訊息")
    async def clear(self, interaction: discord.Interaction, amount: int = 5):
        """清除指定數量的訊息"""
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "你沒有權限執行此指令！",
                ephemeral=True
            )
            return
        
        if amount < 1 or amount > 100:
            await interaction.response.send_message(
                "請輸入 1-100 之間的數字！",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(
            f"已清除 {len(deleted)} 則訊息！",
            ephemeral=True
        )

    @app_commands.command(name="userinfo", description="顯示用戶資訊")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        """顯示用戶資訊"""
        if member is None:
            member = interaction.user
        
        embed = discord.Embed(
            title=f"👤 {member.display_name} 的資訊",
            color=member.color
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="用戶 ID", value=member.id, inline=True)
        embed.add_field(name="加入時間", value=member.joined_at.strftime("%Y/%m/%d"), inline=True)
        embed.add_field(name="帳號建立時間", value=member.created_at.strftime("%Y/%m/%d"), inline=True)
        embed.add_field(name="身分組", value=" ".join([role.mention for role in member.roles[1:]]) or "無", inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="remind", description="設定提醒")
    @app_commands.describe(
        minutes="幾分鐘後提醒（1-1440）",
        message="提醒內容"
    )
    async def set_reminder(self, interaction: discord.Interaction, minutes: int, message: str):
        """設定提醒"""
        # 驗證參數
        if minutes <= 0:
            await interaction.response.send_message(
                "⚠️ 請輸入大於 0 的分鐘數！",
                ephemeral=True
            )
            return
            
        if minutes > 1440:  # 24小時 = 1440分鐘
            await interaction.response.send_message(
                "⚠️ 提醒時間不能超過 24 小時（1440 分鐘）！",
                ephemeral=True
            )
            return
            
        if not message or len(message) > 200:
            await interaction.response.send_message(
                "⚠️ 提醒內容不能為空且不能超過 200 個字元！",
                ephemeral=True
            )
            return
        
        # 設定提醒時間
        remind_time = datetime.now() + timedelta(minutes=minutes)
        time_str = remind_time.strftime("%Y-%m-%d %H:%M")
        
        # 格式化為人類可讀的時間表示
        if minutes < 60:
            time_display = f"{minutes} 分鐘後"
        else:
            hours = minutes // 60
            mins = minutes % 60
            time_display = f"{hours} 小時"
            if mins > 0:
                time_display += f" {mins} 分鐘"
            time_display += "後"
        
        # 加入提醒列表
        if time_str not in self.reminders:
            self.reminders[time_str] = []
        
        reminder_id = f"{interaction.user.id}-{len(self.reminders[time_str])}"
        
        self.reminders[time_str].append({
            "id": reminder_id,
            "user_id": interaction.user.id,
            "channel_id": interaction.channel_id,
            "message": message,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        self.save_reminders()
        
        # 建立回應嵌入式訊息
        embed = discord.Embed(
            title="⏰ 提醒已設定",
            description=f"將在 **{time_display}** 提醒你",
            color=discord.Color.green()
        )
        embed.add_field(name="提醒內容", value=message, inline=False)
        embed.add_field(name="提醒時間", value=time_str, inline=True)
        embed.set_footer(text=f"提醒 ID: {reminder_id}")
        
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @app_commands.command(name="help", description="顯示機器人命令幫助")
    async def help_command(self, interaction: discord.Interaction):
        """顯示機器人所有可用命令的幫助信息"""
        embed = discord.Embed(
            title="🤖 派對機器人使用指南",
            description="以下是所有可用的指令，使用斜線 `/` 開始輸入命令",
            color=discord.Color.blue()
        )
        
        # 音樂功能
        embed.add_field(
            name="🎵 音樂指令",
            value=(
                "`/play <歌曲>` - 播放音樂\n"
                "`/skip` - 跳過當前歌曲\n"
                "`/loop` - 切換循環播放\n"
                "`/stop` - 停止播放並清空佇列"
            ),
            inline=False
        )
        
        # 娛樂功能
        embed.add_field(
            name="🎮 娛樂指令",
            value=(
                "`/random` - 從語音頻道隨機抽選一人\n"
                "`/dice_roll [最大值]` - 擲骰子\n"
                "`/poll <問題> <選項>` - 建立投票\n"
                "`/emoji <文字>` - 獲取表情符號推薦\n"
                "`/party_gif [類別]` - 獲取隨機 GIF"
            ),
            inline=False
        )
        
        # 實用工具
        embed.add_field(
            name="🔧 實用工具",
            value=(
                "`/userinfo [用戶]` - 顯示用戶資訊\n"
                "`/remind <分鐘> <訊息>` - 設定提醒\n"
                "`/clear [數量]` - 清除訊息 (需管理權限)"
            ),
            inline=False
        )
        
        # 設置嵌入訊息底部
        bot_version = "1.0.0"
        embed.set_footer(
            text=f"派對機器人 v{bot_version} | 使用 /help 查看此幫助",
            icon_url=self.bot.user.display_avatar.url if self.bot.user.avatar else None
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    """設置 Utils cog"""
    await bot.add_cog(Utils(bot))
