# 🔧 DC_partybot 環境配置指南

本指南將引導您完成 Discord 機器人的環境配置。

## 📋 必需的 API 金鑰

### 1. Discord Bot Token（必須）

#### 步驟 1：創建 Discord 應用程式
1. 前往 [Discord Developer Portal](https://discord.com/developers/applications)
2. 點擊 "New Application" 創建新應用程式
3. 輸入應用程式名稱（例如：DC_partybot）

#### 步驟 2：創建機器人
1. 在左側選單中點擊 "Bot"
2. 點擊 "Add Bot" 創建機器人
3. 在 "Token" 區域點擊 "Copy" 複製 Token

#### 步驟 3：設置機器人權限
在 "Bot Permissions" 區域勾選以下權限：
- `Send Messages` - 發送訊息
- `Use Slash Commands` - 使用斜線指令
- `Connect` - 連接語音頻道
- `Speak` - 在語音頻道說話
- `Use Voice Activity` - 使用語音活動
- `Manage Messages` - 管理訊息（清除功能）
- `Add Reactions` - 添加反應
- `Read Message History` - 讀取訊息歷史

### 2. YouTube API Key（音樂功能必須）

#### 步驟 1：啟用 YouTube Data API
1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 創建新專案或選擇現有專案
3. 前往 "APIs & Services" > "Library"
4. 搜尋 "YouTube Data API v3" 並啟用

#### 步驟 2：創建 API 金鑰
1. 前往 "APIs & Services" > "Credentials"
2. 點擊 "Create Credentials" > "API Key"
3. 複製生成的 API 金鑰

### 3. Spotify API（Spotify 功能，可選）

1. 前往 [Spotify for Developers](https://developer.spotify.com/)
2. 登入並創建新應用程式
3. 獲取 Client ID 和 Client Secret

## ⚙️ 配置 .env 檔案

### 步驟 1：創建配置檔案
```bash
# 使用便利腳本創建
.\scripts.ps1 setup-env

# 或手動複製
cp .env.example .env
```

### 步驟 2：編輯 .env 檔案
用文字編輯器開啟 `.env` 檔案，填入獲得的 API 金鑰：

```env
# Discord Bot Token (必須)
DISCORD_TOKEN=your_actual_discord_token_here

# YouTube API Key (音樂功能必須)
YOUTUBE_API_KEY=your_actual_youtube_api_key_here



# Spotify API (可選)
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret

# 其他配置保持預設值即可
REDIS_URL=redis://localhost:6379
COMMAND_PREFIX=!
DEBUG_MODE=false
LOG_LEVEL=INFO
```

## 🚀 啟動機器人

### 確認配置
```bash
# 檢查環境是否正確設置
uv run python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('Discord Token:', 'SET' if os.getenv('DISCORD_TOKEN') else 'NOT SET')"
```

### 啟動機器人
```bash
# 使用便利腳本
.\scripts.ps1 run

# 或直接使用 uv
uv run python main.py
```

## 🔗 邀請機器人到伺服器

### 步驟 1：生成邀請連結
1. 回到 [Discord Developer Portal](https://discord.com/developers/applications)
2. 選擇您的應用程式
3. 點擊左側的 "OAuth2" > "URL Generator"
4. 在 "Scopes" 中勾選：
   - `bot`
   - `applications.commands`
5. 在 "Bot Permissions" 中勾選需要的權限
6. 複製生成的 URL

### 步驟 2：邀請機器人
1. 在瀏覽器中開啟複製的 URL
2. 選擇要加入的伺服器
3. 確認權限並邀請

## 🛠️ 故障排除

### 常見問題

#### 1. "找不到 DISCORD_TOKEN" 錯誤
- 檢查 `.env` 檔案是否存在
- 確認 `DISCORD_TOKEN` 是否正確填入
- 確認沒有多餘的空格或引號

#### 2. 機器人無法播放音樂
- 確認 `YOUTUBE_API_KEY` 是否正確設置
- 檢查 YouTube Data API 是否已啟用
- 確認 FFmpeg 已正確安裝

#### 3. 機器人無法連接語音頻道
- 確認機器人有 "Connect" 和 "Speak" 權限
- 檢查語音頻道是否已滿
- 確認用戶是否在語音頻道中

### 除錯模式
在 `.env` 檔案中設置：
```env
DEBUG_MODE=true
LOG_LEVEL=DEBUG
```

這將提供更詳細的日誌資訊幫助診斷問題。

## 📚 更多資源

- [Discord.py 文檔](https://discordpy.readthedocs.io/)
- [Discord Developer Portal](https://discord.com/developers/docs)
- [YouTube Data API 文檔](https://developers.google.com/youtube/v3)
- [專案 GitHub 頁面](https://github.com/jimmy071919/DC_partybot)

---

**注意：** 請勿將 `.env` 檔案提交到版本控制系統中。該檔案包含敏感資訊，應該保持私密。