# 使用官方 Python 3.11 slim 映像
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 複製需求文件並安裝 Python 依賴
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 複製應用程式碼
COPY . .

# 建立必要的目錄並設定權限
RUN mkdir -p data logs \
    && chmod -R 755 /app

# 設定環境變數
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PYTHONIOENCODING=utf-8

# 建立非 root 使用者
RUN groupadd -r botuser && useradd -r -g botuser botuser \
    && chown -R botuser:botuser /app
USER botuser

# 健康檢查（使用 requests 檢查 Discord API）
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('https://discord.com/api/v10/gateway', timeout=5)"

# 運行應用程式
CMD ["python", "main.py"]