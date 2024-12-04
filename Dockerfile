FROM python:3.11-slim

# 設置工作目錄
WORKDIR /app

# 安裝系統依賴和 ffmpeg
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    build-essential \
    python3-dev \
    libffi-dev \
    libnacl-dev \
    && rm -rf /var/lib/apt/lists/*

# 驗證 ffmpeg 安裝
RUN ffmpeg -version

# 複製依賴文件
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式代碼
COPY . .

# 確保音樂目錄存在
RUN mkdir -p /app/music_cache

# 設置環境變數
ENV PYTHONUNBUFFERED=1
ENV PATH="/usr/local/bin:${PATH}"

# 運行機器人
CMD ["python", "main.py"]
