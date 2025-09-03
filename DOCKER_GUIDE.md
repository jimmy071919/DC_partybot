# Docker 部署指南

## 前置準備

1. **確保 Docker 已安裝**
   - Docker Desktop（Windows/Mac）
   - Docker Engine（Linux）

2. **準備環境變數檔案**
   ```bash
   cp .env.example .env
   ```
   然後編輯 `.env` 檔案，填入你的 API 金鑰：
   - `DISCORD_TOKEN`: Discord 機器人的 Token
   - `YOUTUBE_API_KEY`: YouTube API 金鑰
   - `TENOR_API_KEY`: Tenor API 金鑰

## 啟動方式

### 方式一：使用 Docker Compose（推薦）

```bash
# 構建並啟動容器
docker-compose up -d

# 查看日誌
docker-compose logs -f discord-bot

# 停止服務
docker-compose down
```

### 方式二：使用 Docker 指令

```bash
# 構建映像
docker build -t dc_partybot .

# 運行容器
docker run -d \
  --name dc_partybot \
  --env-file .env \
  -v ./data:/app/data \
  -v ./discord_bot.log:/app/discord_bot.log \
  -v ./youtube.cookies:/app/youtube.cookies \
  --restart unless-stopped \
  dc_partybot
```

## 管理指令

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
   docker exec dc_partybot env | grep -E "(DISCORD|YOUTUBE|TENOR)"
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
