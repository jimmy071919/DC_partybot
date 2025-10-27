# Discord Bot Docker 管理
.PHONY: build up down logs restart clean help

# 預設目標
help:
	@echo "Discord Bot Docker 管理指令："
	@echo "  make build    - 建置 Docker 映像"
	@echo "  make up       - 啟動服務"
	@echo "  make down     - 停止服務"
	@echo "  make logs     - 查看日誌"
	@echo "  make restart  - 重新啟動服務"
	@echo "  make clean    - 清理所有 Docker 資源"

# 建置映像
build:
	docker-compose build

# 啟動服務
up:
	docker-compose up -d

# 停止服務
down:
	docker-compose down

# 查看日誌
logs:
	docker-compose logs -f discord-bot

# 重新啟動
restart:
	docker-compose restart

# 清理資源
clean:
	docker-compose down --rmi all --volumes --remove-orphans