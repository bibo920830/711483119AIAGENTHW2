FROM python:3.11-slim

# 避免 Python 產生 .pyc 檔並確保 stdout 即時輸出不緩衝
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# 先複製並安裝套件以善用容器層快取
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製核心原始碼
COPY src/ ./src/

# 預設啟動指令：執行內建測試案例與完整 Trace 展示
CMD ["python", "src/main.py"]