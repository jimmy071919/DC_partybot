# DC_partybot - Discord 派對機器人

一個功能豐富的 Discord 機器人，專為派對、娛樂和社群互動而設計。

## 🌟 主要功能

### 🎵 音樂播放
- **YouTube 搜尋與播放**：直接從 YouTube 搜尋和播放音樂
- **佇列管理**：添加歌曲到佇列並管理播放順序
- **播放控制**：跳過、循環播放、停止等功能

### 😄 表情符號
- **表情符號推薦**：根據訊息內容推薦合適的表情符號

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
1. Python 3.11+
2. 安裝 ffmpeg（用於音樂播放）
3. Discord Bot Token 和 YouTube API Key

> 📖 **詳細設置指南：** 請參閱 [SETUP_GUIDE.md](./SETUP_GUIDE.md) 獲取完整的 API 金鑰申請和環境配置說明

### 安裝步驟

#### 使用 uv（推薦）
1. 安裝 [uv](https://docs.astral.sh/uv/) Python 套件管理器
2. 克隆此專案：
```bash
git clone https://github.com/jimmy071919/DC_partybot.git
cd DC_partybot
```

3. 安裝依賴：
```bash
uv sync
```

4. 設置環境變數：
```bash
# 使用便利腳本創建環境檔案
.\scripts.ps1 setup-env

# 然後編輯 .env 文件填入 API 金鑰
# 詳細步驟請參閱 SETUP_GUIDE.md
```

5. 啟動機器人：
```bash
# 使用便利腳本（推薦）
.\scripts.ps1 run

# 或直接使用 uv
uv run python main.py
```

#### 傳統方式（pip）
1. 確保安裝 Python 3.11+
2. 克隆專案並進入目錄
3. 安裝依賴：`pip install -r requirements.txt.backup`
4. 設置環境變數並啟動：`python main.py`

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

- `/userinfo [用戶]` - 顯示用戶資訊
- `/remind <分鐘> <訊息>` - 設定提醒
- `/clear [數量]` - 清除訊息
- `/help` - 查看所有可用指令

## 🚀 開發工具

本專案使用 [uv](https://docs.astral.sh/uv/) 作為 Python 套件管理器，提供更快的安裝速度和更好的依賴管理。

### 常用命令
```bash
# 安裝依賴
uv sync

# 添加新套件
uv add <package-name>

# 運行機器人
uv run python main.py

# 開發工具
uv run black .          # 代碼格式化
uv run flake8 .         # 代碼檢查
uv run mypy .           # 類型檢查
uv run pytest          # 運行測試
```

### PowerShell 便利腳本
```bash
.\scripts.ps1 help      # 查看所有可用命令
.\scripts.ps1 run       # 啟動機器人
.\scripts.ps1 format    # 格式化代碼
.\scripts.ps1 lint      # 執行 linting
.\scripts.ps1 clean     # 清理暫存檔案
```

## ⚙️ 環境要求
- Python 3.11+
- discord.py 2.6+
- FFmpeg
- YouTube API 金鑰


## 🔧 配置與擴展

如果需要進一步配置或擴展功能，可以修改以下檔案：
- `config.py` - 機器人配置
- `emoji_data.json` - 表情符號關鍵字數據
- 各種 cog 檔案 - 新增或修改功能模組

## 🤝 貢獻指南

歡迎提交 Pull Request 或 Issue 以改進此機器人！

## 📄 授權

此專案採用 MIT 授權協議 - 詳見 LICENSE 文件