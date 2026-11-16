# 📈 MACET FINANCE RESEARCH - VIETNAM STOCK INVESTMENT BOT

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Aiogram](https://img.shields.io/badge/Aiogram-3.x-2CA5E0.svg)](https://docs.aiogram.dev/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Hệ thống Bot tự động giám sát thông tin vĩ mô, phân tích kỹ thuật và quản lý danh mục đầu tư mô phỏng (quỹ 1.000.000.000 VNĐ) cho thị trường chứng khoán Việt Nam (HOSE, HNX, UPCoM), đồng bộ thông báo và bảng biểu realtime lên Kênh Telegram.

---

## 🌟 TÍNH NĂNG NỔI BẬT

### 1. Phương pháp đầu tư Top-Down Macro (Vĩ mô -> Ngành -> Cổ phiếu)
- **Ưu tiên nhóm ngành dẫn sóng**: Tự động nhận diện và cập nhật danh sách các ngành được hưởng lợi vĩ mô mạnh mẽ nhất (Công nghệ & Bán dẫn, Thép, Đầu tư công & Hạ tầng, Năng lượng,...).
- **Phân loại tin tức thông minh**:
  - *Tin vĩ mô đa ngành / tổng quan*: Đưa vào diện theo dõi toàn ngành, không gán ép vào một mã cổ phiếu riêng lẻ.
  - *Tin ngành & doanh nghiệp cụ thể*: Định vị ngay cổ phiếu Leader đầu ngành để phân tích kỹ thuật và ra quyết định đầu tư.
- **Tối ưu tỷ trọng**: Nhóm ngành ưu tiên vĩ mô được nâng hạn mức phân bổ vốn (6.0% - 7.5% giá trị quỹ) và quota tối đa 3 mã/ngành.

### 2. Giao dịch theo khung giờ thực tế Sàn Chứng khoán Việt Nam
- **Phiên giao dịch chính thức**: Chỉ mở vị thế mua/bán và kích hoạt chốt lời/cắt lỗ trong các khung giờ:
  - Phiên sáng: `09:00 - 11:30`
  - Phiên chiều: `13:00 - 15:00` (Thứ Hai đến Thứ Sáu)
- **Xử lý ngoài giờ & Giờ nghỉ trưa**: Khi tin tức xuất hiện vào giờ nghỉ trưa (`11:30 - 13:00`), buổi tối hoặc cuối tuần:
  - Bot sẽ lưu lệnh vào hàng đợi **Lệnh chờ (`pending_orders`)** với trạng thái *💼 Quyết định (Chờ mở phiên)*.
  - Ngay khi thị trường mở phiên kế tiếp (`09:00` hoặc `13:00`), bot tự động lấy thị giá mở cửa thực tế, khớp lệnh và gửi thông báo xác nhận lên Kênh.

### 3. Quản trị Danh mục & Vốn quỹ (1.000.000.000 VNĐ)
- **Đa dạng hóa danh mục**: Tối đa lên đến 15 mã cổ phiếu thuộc nhiều nhóm ngành khác nhau để phân tán rủi ro.
- **Kỷ luật giao dịch chặt chẽ**:
  - Mục tiêu Chốt lời: `+12.0%`
  - Ngưỡng Cắt lỗ: `-6.0%`
  - Giám sát realtime biến động thị giá trong phiên.
- **Cơ chế kiểm soát Room & Tiền mặt**:
  - Khi tiền mặt khả dụng **< 50.000.000 VNĐ** hoặc danh mục đã đủ số lượng: Tạm dừng quét tin cổ phiếu mới ngoài danh mục, chỉ tập trung đưa tin và giám sát các mã đang nắm giữ.
  - Khi bán chốt lời/cắt lỗ thu hồi vốn hoặc danh mục còn room: Tự động kích hoạt lại bộ lọc tìm kiếm cơ hội mới.

### 4. Báo cáo Tổng kết Cuối phiên (15:30) & Tự động Ghim
- Mỗi 15:30 chiều các ngày giao dịch, hệ thống tự động tổng hợp toàn bộ danh mục, tính toán thị giá, lãi/lỗ và tỷ trọng tiền mặt/cổ phiếu.
- Xuất hình ảnh đồ họa chất lượng cao chuẩn giao diện Dark Mode phong cách Terminal chuyên nghiệp (phân bố cột ngay ngắn, định dạng số chuẩn VND).
- **Tự động Ghim (Pin)** hình ảnh bảng tổng kết lên đầu Kênh Telegram để người theo dõi dễ dàng nắm bắt.

### 5. Phân tích Kỹ thuật (TA) & Vẽ Chart nến
- Tự động lấy dữ liệu nến OHLCV từ nguồn dữ liệu chứng khoán tốc độ cao.
- Tính toán nhanh các chỉ báo quan trọng: RSI(14), MACD, MA20, MA50, Khối lượng giao dịch & phát hiện Volume bùng nổ.
- Tạo đồ thị nến Nhật trực quan với chỉ báo kỹ thuật gửi kèm nhận định.

---

## 📁 CẤU TRÚC MÃ NGUỒN

```text
├── .env.example                  # File mẫu cấu hình biến môi trường
├── .gitignore                    # Chặn commit thông tin nhạy cảm và database
├── Dockerfile                    # Đóng gói Docker container
├── docker-compose.yml            # Khởi chạy một lệnh với Docker Compose
├── requirements.txt              # Danh sách thư viện Python cần thiết
├── config.py                     # Quản lý đọc biến môi trường
├── db.py                         # Khởi tạo và quản lý cơ sở dữ liệu SQLite
├── data_fetcher.py               # Lấy nến giá chứng khoán & tin RSS CafeF
├── technical_analysis.py         # Tính toán chỉ báo TA (MA, RSI, MACD)
├── chart_generator.py            # Vẽ đồ thị nến kỹ thuật
├── ai_analyzer.py                # Phân tích tin tức & chiến lược vĩ mô
├── investment_engine.py          # Bộ máy ra quyết định phân bổ vốn & kiểm tra room
├── pending_order_executor.py     # Hàng đợi và khớp lệnh chờ đầu phiên giao dịch
├── portfolio_manager.py          # Quản lý số dư, mở/đóng vị thế và tính NAV
├── portfolio_monitor.py          # Giám sát chốt lời (+12%) & cắt lỗ (-6%)
├── table_image_generator.py      # Tạo ảnh bảng biểu danh mục 15:30 chuyên nghiệp
├── closing_portfolio_broadcaster.py # Gửi và Ghim ảnh tổng kết lúc 15:30
├── news_broadcaster.py           # Quét tin tức và phát thông báo 2 phân đoạn lên Kênh
├── macro_broadcaster.py          # Điểm tin vĩ mô buổi sáng (08:30)
├── holiday_checker.py            # Kiểm tra ngày nghỉ lễ & giờ giao dịch sàn VN
├── bot.py                        # Entrypoint chính điều khiển bot và lập lịch tiến trình
├── reset_portfolio.py            # Script làm mới dữ liệu quỹ về 1 tỷ tiền mặt
└── seed_priorities.py            # Script cập nhật các nhóm ngành ưu tiên vĩ mô
```

---

## ⚙️ CÀI ĐẶT & CHẠY TẠI MÁY CỤC BỘ (LOCAL)

### 1. Yêu cầu hệ thống
- Python 3.10 trở lên.
- Đã cài đặt `git`.

### 2. Thiết lập môi trường
```bash
# Clone repository
git clone https://github.com/your-username/macet-finance-bot.git
cd macet-finance-bot

# Tạo môi trường ảo
python -m venv venv

# Kích hoạt môi trường ảo:
# Trên Windows:
.\venv\Scripts\activate
# Trên Linux/macOS:
source venv/bin/activate

# Cài đặt thư viện
pip install -r requirements.txt
```

### 3. Cấu hình biến môi trường
Tạo file `.env` từ file mẫu:
```bash
cp .env.example .env
```
Mở file `.env` và điền thông tin thực tế:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHANNEL_ID=@your_channel_username
TELEGRAM_CHANNEL_USERNAME=@your_channel_username
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.5-flash-lite
AUTO_NEWS_INTERVAL_SECONDS=300
```

### 4. Khởi chạy bot
```bash
python bot.py
```

---

## 🔒 HƯỚNG DẪN ĐẨY LÊN GITHUB PUBLIC AN TOÀN 100%

Dự án đã được thiết lập sẵn file `.gitignore` để **loại trừ hoàn toàn các thông tin nhạy cảm**:
- File `.env` chứa token và API key không bao giờ bị đưa lên Git.
- File cơ sở dữ liệu `finance_bot.db` chứa lịch sử tài khoản của bạn được giữ kín tại máy.
- Các file ảnh tạm thời, cache Python (`__pycache__`) được tự động bỏ qua.

### Các bước đẩy code lên GitHub:
1. **Kiểm tra trạng thái Git để đảm bảo an toàn:**
   ```bash
   git status
   ```
   *Đảm bảo không xuất hiện file `.env` hay file `.db` trong danh sách Untracked files.*

2. **Commit mã nguồn:**
   ```bash
   git add .
   git commit -m "feat: initial commit Macet Finance Research bot"
   ```

3. **Liên kết với Repository GitHub của bạn và đẩy lên:**
   ```bash
   git branch -M main
   git remote add origin https://github.com/<tai-khoan-cua-ban>/<ten-repo>.git
   git push -u origin main
   ```

---

## ☁️ TRIỂN KHAI CHẠY 24/24 REALTIME MILISECOND (KHÔNG CẦN BẬT MÁY)

Để bot hoạt động liên tục 24/7 với độ trễ phản hồi cực thấp (vài mili-giây) mà **không cần bật máy tính cá nhân**, giải pháp tối ưu nhất là sử dụng một máy chủ ảo **Cloud VPS**.

### 💡 Tại sao nên dùng Cloud VPS đặt tại Singapore hoặc Việt Nam?
- **Độ trễ mili-giây (Low Latency)**: Ping đến API dữ liệu chứng khoán Việt Nam (`dchart-api.vndirect.com.vn`) chỉ từ **1 - 5 ms** (nếu VPS ở VN) hoặc **15 - 25 ms** (nếu VPS ở Singapore).
- **Chi phí cực rẻ**: Chỉ từ **50.000 - 90.000 VNĐ/tháng** (~$2 - $3/tháng) tại các nhà cung cấp như *Vietnix, AZDIGI, TinoHost, Hetzner, Vultr, DigitalOcean*.
- **Hoạt động độc lập**: Chạy liên tục cả năm, không lo mất điện, mất mạng hay máy tính bị tắt/sleep.

---

### CÁCH 1: Chạy bằng Docker Compose trên VPS (Khuyên dùng - Nhanh nhất)

1. **Kết nối SSH vào VPS của bạn:**
   ```bash
   ssh root@<ip_vps>
   ```

2. **Cài đặt Docker & Git (nếu VPS mới):**
   ```bash
   apt update && apt install -y git docker.io docker-compose
   ```

3. **Clone repo và tạo file cấu hình `.env`:**
   ```bash
   git clone https://github.com/<tai-khoan-cua-ban>/<ten-repo>.git
   cd <ten-repo>
   nano .env
   ```
   *(Dán các thông tin token Telegram, Gemini API Key của bạn vào rồi lưu lại bằng `Ctrl + O` -> `Enter` -> `Ctrl + X`)*

4. **Khởi chạy bot dưới nền 24/7:**
   ```bash
   docker-compose up -d --build
   ```
   *Bot sẽ tự động build, khởi chạy ngầm, tự bật lại nếu server khởi động lại và duy trì độ trễ chỉ vài mili-giây.*

5. **Xem log realtime của bot:**
   ```bash
   docker-compose logs -f
   ```

---

### CÁCH 2: Chạy trực tiếp bằng tiến trình Systemd trên Linux VPS

Nếu không muốn dùng Docker, bạn có thể tạo một service hệ thống `systemd`:

1. **Tạo service file:**
   ```bash
   sudo nano /etc/systemd/system/macet-bot.service
   ```

2. **Dán cấu hình sau (thay đổi đường dẫn cho đúng):**
   ```ini
   [Unit]
   Description=Macet Finance Investment Bot
   After=network.target

   [Service]
   Type=simple
   User=root
   WorkingDirectory=/root/macet-finance-bot
   ExecStart=/root/macet-finance-bot/venv/bin/python bot.py
   Restart=always
   RestartSec=5
   Environment=PYTHONUNBUFFERED=1

   [Install]
   WantedBy=multi-user.target
   ```

3. **Kích hoạt và chạy service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable macet-bot
   sudo systemctl start macet-bot
   ```

4. **Kiểm tra trạng thái hoạt động:**
   ```bash
   sudo systemctl status macet-bot
   ```

---

### CÁCH 3: Triển khai 1-Click trên Cloud PaaS Miễn phí (Render.com)

Nếu chưa muốn thuê VPS, bạn có thể sử dụng **Render.com** (hoặc Railway.app):
1. Đẩy code lên GitHub cá nhân (theo hướng dẫn bảo mật ở trên).
2. Đăng ký tài khoản tại [Render.com](https://render.com) và chọn **New +** -> **Background Worker**.
3. Kết nối với GitHub repository vừa tạo.
4. Cấu hình:
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
5. Tại mục **Environment Variables**, thêm từng cặp khóa:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHANNEL_ID`
   - `TELEGRAM_CHANNEL_USERNAME`
   - `GEMINI_API_KEY`
   - `GEMINI_MODEL`
6. Nhấn **Deploy**. Bot sẽ tự động chạy trên Cloud 24/7.
*(Lưu ý: Đối với tài khoản miễn phí trên các PaaS như Render, file database SQLite có thể bị reset khi restart container nếu không gắn Persistent Disk).*

---

## ⚠️ TUYÊN BỐ MIỄN TRỪ TRÁCH NHIỆM (DISCLAIMER)

- Mọi quyết định giao dịch và phân bổ danh mục được tạo bởi bot là **hoàn toàn mô phỏng trên vốn giả định (Paper Trading)** nhằm mục đích nghiên cứu, theo dõi và tham khảo chiến lược thị trường.
- Người dùng tự chịu trách nhiệm đối với mọi quyết định tài chính thực tế của mình.

---

**Macet Finance Research** • *Hệ thống Giám sát & Quản trị Danh mục Đầu tư Tự động*
