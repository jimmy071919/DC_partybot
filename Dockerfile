# 使用官方 Python 3.11 slim 映像
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 設定環境變數
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV PYTHONHTTPSVERIFY=0
ENV PYTHONDONTWRITEBYTECODE=1

# 複製 pyproject.toml 並安裝依賴
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# 複製應用程式碼
COPY . .

# 建立必要的目錄並設定權限
RUN mkdir -p data logs \
    && chmod 755 data logs

# 驗證 FFmpeg 安裝
RUN ffmpeg -version > /dev/null 2>&1 && echo "FFmpeg installed successfully"

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# 運行應用程式
CMD ["python", "main.py"]