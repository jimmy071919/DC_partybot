FROM python:3.10-slim

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 複製應用程式文件
COPY . .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 確保 cookies 文件有正確的權限
COPY youtube.cookies /app/youtube.cookies
RUN chmod 644 /app/youtube.cookies

CMD ["python", "bot.py"]
