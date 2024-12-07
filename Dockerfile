# 使用更完整的 Python 映像
FROM python:3.9-slim

# 安裝系統依賴和 FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 設定工作目錄
WORKDIR /app

# 複製專案檔案
COPY . .

# 安裝 Python 依賴
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 設定環境變數
ENV PYTHONUNBUFFERED=1

# 執行指令
CMD ["python", "main.py"]
