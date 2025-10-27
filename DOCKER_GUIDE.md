# Docker 部署指南

# Docker 部署指南

## 前置準備

1. **安裝 Docker**
   - 下載並安裝 [Docker Desktop](https://www.docker.com/products/docker-desktop/)

2. **設定環境變數**
   - 複製範例環境檔案：
   ```bash
   cp .env.example .env
   ```
   - 編輯 `.env` 檔案，填入以下內容：
   ```
   DISCORD_TOKEN=你的Discord機器人Token
   YOUTUBE_API_KEY=你的YouTube_API金鑰
   COMMAND_PREFIX=!
   ```

## 快速啟動

```bash
# 建置並啟動
docker-compose up -d

# 查看日誌
docker-compose logs -f discord-bot

# 停止服務
docker-compose down
```

## 基本指令

```bash
# 重新建置
docker-compose build

# 重新啟動
docker-compose restart

# 檢查狀態
docker-compose ps

# 查看即時日誌
docker-compose logs -f

# 進入容器（除錯用）
docker-compose exec discord-bot /bin/bash
```

## 故障排除

### 常見問題

1. **機器人無法啟動**
   - 檢查 `.env` 檔案是否正確設定
   - 確認 Discord Token 和 YouTube API Key 有效

2. **音樂播放問題**
   - 容器已包含 FFmpeg，本地環境的 FFmpeg 錯誤不影響 Docker 部署

3. **查看詳細錯誤**
   ```bash
   docker-compose logs discord-bot
   ```

## 檔案結構

```
.
├── Dockerfile          # Docker 映像建置檔案
├── docker-compose.yml  # Docker Compose 配置檔案
├── .dockerignore       # Docker 忽略檔案清單
├── .env.example        # 環境變數範例檔案
└── DOCKER_GUIDE.md     # 本檔案
```

就這麼簡單！機器人現在應該在 Docker 容器中順利運行了。

```bash
# 查看容器狀態
docker ps

# 查看容器日誌
docker logs dc_partybot -f

# 進入容器內部
docker exec -it dc_partybot /bin/bash

# 重啟容器
docker restart dc_partybot

# 停止並移除容器
docker stop dc_partybot
docker rm dc_partybot

# 移除映像
docker rmi dc_partybot
```

## 更新部署

```bash
# 重新構建並啟動
docker-compose up -d --build

# 或者手動操作
docker-compose down
docker-compose build
docker-compose up -d
```

## 故障排除

1. **檢查日誌**
   ```bash
   docker-compose logs discord-bot
   ```

2. **檢查容器狀態**
   ```bash
   docker ps -a
   ```

3. **檢查環境變數**
   ```bash
   docker exec dc_partybot env | grep -E "(DISCORD|YOUTUBE)"
   ```

4. **重建容器**
   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

## 注意事項

- 確保 `.env` 檔案包含所有必要的 API 金鑰
- 數據持久化通過 volumes 掛載實現
- 日誌檔案會同步到主機
- 容器會自動重啟（除非手動停止）
