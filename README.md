# DC_partybot - Discord 派對機器人

一個功能豐富的 Discord 機器人，專為派對、娛樂和社群互動而設計。

## 🌟 主要功能

### 🎵 音樂播放
- **YouTube 搜尋與播放**：直接從 YouTube 搜尋和播放音樂
- **佇列管理**：添加歌曲到佇列並管理播放順序
- **播放控制**：跳過、循環播放、停止等功能

### 😄 表情符號與 GIF
- **表情符號推薦**：根據訊息內容推薦合適的表情符號
- **GIF 搜尋**：搜尋並分享各種情緒/派對相關的 GIF

### 🎮 娛樂功能
- **隨機抽選**：從語音頻道中隨機抽選成員
- **擲骰子**：產生隨機數字
- **投票系統**：創建具有多個選項的投票

### ⏰ 實用工具
- **提醒功能**：設定時間提醒
- **訊息管理**：清除指定數量的訊息
- **用戶資訊**：查看成員資訊

## 🚀 快速開始

### 準備工作
1. 安裝 Python 3.8+ 和 pip
2. 安裝 ffmpeg（用於音樂播放）
3. 在 Discord Developer Portal 建立機器人

### 安裝步驟
1. 克隆此專案：
```bash
git clone https://github.com/yourusername/DC_partybot.git
cd DC_partybot
```

2. 安裝依賴：
```bash
pip install -r requirements.txt
```

3. 設置環境變數：
```bash
cp .env.example .env
```
然後編輯 `.env` 文件填入必要的 API 金鑰

4. 啟動機器人：
```bash
python main.py
```

## 📝 指令列表

### 斜線指令 (/)
- `/play <歌曲>` - 播放音樂
- `/skip` - 跳過當前歌曲
- `/loop` - 切換循環播放
- `/stop` - 停止播放
- `/random` - 隨機抽選一人
- `/dice_roll [最大值]` - 擲骰子
- `/poll <問題> <選項>` - 建立投票
- `/emoji <文字>` - 獲取表情符號推薦
- `/party_gif [類別]` - 獲取隨機 GIF
- `/userinfo [用戶]` - 顯示用戶資訊
- `/remind <分鐘> <訊息>` - 設定提醒
- `/clear [數量]` - 清除訊息
- `/help` - 查看所有可用指令

## ⚙️ 環境要求
- Python 3.8+
- discord.py 2.3+
- FFmpeg
- YouTube API 金鑰
- Tenor API 金鑰

## 🔧 配置與擴展

如果需要進一步配置或擴展功能，可以修改以下檔案：
- `config.py` - 機器人配置
- `emoji_data.json` - 表情符號和 GIF 關鍵字數據
- 各種 cog 檔案 - 新增或修改功能模組

## 🤝 貢獻指南

歡迎提交 Pull Request 或 Issue 以改進此機器人！

## 📄 授權

此專案採用 MIT 授權協議 - 詳見 LICENSE 文件