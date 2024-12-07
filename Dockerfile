FROM python:3.9-slim

# 設置工作目錄
WORKDIR /app

# 複製依賴文件
COPY requirements.txt .

# 安裝依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案文件
COPY . .

# 設置環境變量
ENV PYTHONUNBUFFERED=1

# 運行命令
CMD ["python", "main.py"]
