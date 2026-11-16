from datetime import datetime, date
from typing import Optional, Set
from zoneinfo import ZoneInfo

VIETNAM_TZ = ZoneInfo("Asia/Bangkok")

# Danh sách các ngày nghỉ lễ của thị trường chứng khoán Việt Nam (HOSE, HNX)
# Định dạng YYYY-MM-DD
VIETNAM_STOCK_HOLIDAYS: Set[str] = {
    # 2025
    "2025-01-01",  # Tết Dương Lịch
    "2025-01-27", "2025-01-28", "2025-01-29", "2025-01-30", "2025-01-31",  # Tết Nguyên Đán
    "2025-04-07",  # Giỗ Tổ Hùng Vương
    "2025-04-30",  # Giải phóng miền Nam
    "2025-05-01", "2025-05-02",  # Quốc tế Lao động
    "2025-09-01", "2025-09-02",  # Quốc Khánh

    # 2026
    "2026-01-01",  # Tết Dương Lịch
    "2026-02-16", "2026-02-17", "2026-02-18", "2026-02-19", "2026-02-20",  # Tết Bính Ngọ
    "2026-04-26", "2026-04-27",  # Giỗ Tổ Hùng Vương (nghỉ bù)
    "2026-04-30",  # 30/4
    "2026-05-01",  # 1/5
    "2026-09-01", "2026-09-02",  # Quốc Khánh

    # 2027
    "2027-01-01",
    "2027-02-05", "2027-02-08", "2027-02-09", "2027-02-10", "2027-02-11",
    "2027-04-15",
    "2027-04-30",
    "2027-05-03",
    "2027-09-01", "2027-09-02"
}

def is_vietnam_trading_day(dt: Optional[datetime] = None) -> bool:
    """
    Kiểm tra xem ngày hôm nay có phải là ngày mở cửa giao dịch của sàn chứng khoán VN hay không.
    Trả về False nếu là Thứ Bảy, Chủ Nhật hoặc ngày nghỉ lễ.
    """
    if dt is None:
        dt = datetime.now(VIETNAM_TZ)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=VIETNAM_TZ)
    else:
        dt = dt.astimezone(VIETNAM_TZ)

    # 1. Kiểm tra cuối tuần (Thứ 7 = 5, Chủ Nhật = 6)
    if dt.weekday() >= 5:
        return False

    # 2. Kiểm tra ngày lễ
    date_str = dt.strftime("%Y-%m-%d")
    if date_str in VIETNAM_STOCK_HOLIDAYS:
        return False

    return True

def is_market_open(dt: Optional[datetime] = None) -> bool:
    """
    Kiểm tra xem sàn chứng khoán Việt Nam (HOSE, HNX, UPCoM) hiện tại có ĐANG TRONG PHIÊN GIAO DỊCH hay không:
    - Phải là ngày giao dịch (Thứ 2 - Thứ 6, không phải ngày lễ).
    - Khung giờ giao dịch thực tế:
      + Phiên Sáng: 09:00 - 11:30
      + Phiên Chiều: 13:00 - 15:00 (14:45 hết phiên khớp lệnh định kỳ ATC, 15:00 hết PLO)
    - Nghỉ trưa (11:30 - 13:00): Trả về False.
    - Ngoài giờ (sau 15:00 hoặc trước 09:00): Trả về False.
    """
    if dt is None:
        dt = datetime.now(VIETNAM_TZ)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=VIETNAM_TZ)
    else:
        dt = dt.astimezone(VIETNAM_TZ)

    if not is_vietnam_trading_day(dt):
        return False

    hour = dt.hour
    minute = dt.minute

    # 1. Phiên Sáng: 09:00 đến 11:30
    if (hour == 9) or (hour == 10) or (hour == 11 and minute <= 30):
        return True

    # 2. Phiên Chiều: 13:00 đến 15:00
    if (hour == 13) or (hour == 14) or (hour == 15 and minute == 0):
        return True

    return False

def get_session_name(dt: Optional[datetime] = None) -> str:
    """Trả về tên phiên giao dịch hiện tại"""
    if dt is None:
        dt = datetime.now(VIETNAM_TZ)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=VIETNAM_TZ)
    else:
        dt = dt.astimezone(VIETNAM_TZ)

    if not is_vietnam_trading_day(dt):
        return "Ngày nghỉ sàn (Cuối tuần / Lễ)"

    hour = dt.hour
    minute = dt.minute

    if (hour == 9) or (hour == 10) or (hour == 11 and minute <= 30):
        return "Phiên Sáng"
    elif hour == 11 and minute > 30 or hour == 12:
        return "Nghỉ Trưa (11:30 - 13:00)"
    elif (hour == 13) or (hour == 14) or (hour == 15 and minute == 0):
        return "Phiên Chiều"
    else:
        return "Ngoài giờ giao dịch"

def get_next_trading_session_desc(dt: Optional[datetime] = None) -> str:
    """Trả về mô tả phiên giao dịch kế tiếp khi thị trường đang đóng cửa"""
    if dt is None:
        dt = datetime.now(VIETNAM_TZ)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=VIETNAM_TZ)
    else:
        dt = dt.astimezone(VIETNAM_TZ)

    is_today_trading = is_vietnam_trading_day(dt)
    hour = dt.hour
    minute = dt.minute

    # Nếu đang là ngày thường
    if is_today_trading:
        if hour < 9:
            return "Phiên Sáng hôm nay (09:00)"
        elif hour == 11 and minute > 30 or hour == 12:
            return "Phiên Chiều hôm nay (13:00)"
        elif hour >= 15:
            # Nếu là Thứ Sáu sau 15:00
            if dt.weekday() == 4:
                return "Phiên Sáng Thứ Hai tuần tới (09:00)"
            else:
                return "Phiên Sáng ngày mai (09:00)"

    # Nếu là Thứ Bảy hoặc Chủ Nhật
    if dt.weekday() == 5:
        return "Phiên Sáng Thứ Hai tuần tới (09:00)"
    elif dt.weekday() == 6:
        return "Phiên Sáng ngày mai (09:00)"

    return "Phiên giao dịch tiếp theo (09:00)"
