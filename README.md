# DC_partybot

一個功能豐富的 Discord 機器人，提供音樂播放、表情符號管理和實用工具功能。

## 功能特點

### 音樂功能

- 支援 YouTube 音樂播放
- 播放列表管理
- 音量控制
- 暫停/繼續播放
- 跳過曲目
- 查看當前播放佇列

### 表情符號管理

- 自定義表情符號添加
- 表情符號搜索
- 表情符號統計

### 實用工具

- 提醒功能
- 伺服器資訊查詢
- 用戶資訊查詢

## 技術架構

- Python 3.9+
- discord.py
- YouTube API
- Tenor API
- FFmpeg（音訊處理）

## 環境要求

- Python 3.9 或更高版本
- FFmpeg
- 網路連接

## 安裝步驟

1. 克隆專案：

```bash
git clone [你的專案URL]
```

2. 安裝依賴：

```bash
pip install -r requirements.txt
```

3. 配置環境變數：
   創建 `.env` 文件並填入以下資訊：

```env
# Discord Bot Configuration
DISCORD_TOKEN=你的Discord令牌

# YouTube API Configuration
YOUTUBE_API_KEY=你的YouTube API金鑰

# Tenor API Configuration
TENOR_API_KEY=你的Tenor API金鑰
```

4. 運行機器人：

```bash
python main.py
```

## 部署

本專案使用 Railway 進行部署，配置檔案包括：

- `railway.toml`：Railway 配置
- `nixpacks.toml`：構建配置

## 文件結構

- `main.py`：主程式入口 啟動此即可
- `music_cog.py`：音樂功能模組
- `emoji_cog.py`：表情符號功能模組
- `utility_cog.py`：實用工具模組
- `spotify.py`：Spotify 相關功能
- `config.py`：配置檔案
- `requirements.txt`：依賴清單

## 配置文件

- `.env`：環境變數配置
- `emoji_data.json`：表情符號資料
- `reminders.json`：提醒功能資料

## 注意事項

1. 請確保 `.env` 文件不被提交到版本控制系統
2. 定期備份重要資料
3. 確保 API 金鑰的安全性

## 維護與更新

- 定期檢查依賴更新
- 監控機器人運行狀態
- 備份重要資料

## 授權

[添加你的授權資訊]

## 支援

如有問題或建議，請提交 Issue 或聯繫開發者。
