FROM python:3.11-slim

# Thiết lập thư mục làm việc
WORKDIR /app

# Cài đặt tzdata thiết lập múi giờ Việt Nam và các font cơ bản hỗ trợ tiếng Việt
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    fonts-liberation \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Asia/Ho_Chi_Minh
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copy file requirements và cài đặt dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn vào container
COPY . .

# Khởi chạy bot
CMD ["python", "bot.py"]
