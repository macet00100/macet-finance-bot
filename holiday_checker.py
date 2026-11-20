from datetime import datetime, date, timedelta
from typing import Optional, Set, Union, Any, Tuple, Dict
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

def parse_vietnam_datetime(val: Any) -> datetime:
    """Chuyển đổi linh hoạt nhiều định dạng ngày/giờ sang datetime có timezone Asia/Bangkok"""
    if isinstance(val, datetime):
        return val.astimezone(VIETNAM_TZ) if val.tzinfo else val.replace(tzinfo=VIETNAM_TZ)
    if isinstance(val, date):
        return datetime(val.year, val.month, val.day, tzinfo=VIETNAM_TZ)
    
    val_str = str(val).strip()
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(val_str, fmt).replace(tzinfo=VIETNAM_TZ)
        except ValueError:
            pass
    return datetime.now(VIETNAM_TZ)

def get_next_trading_day(d: date) -> date:
    """Tìm ngày giao dịch tiếp theo sau ngày d"""
    cur = d + timedelta(days=1)
    while not is_vietnam_trading_day(datetime(cur.year, cur.month, cur.day, tzinfo=VIETNAM_TZ)):
        cur += timedelta(days=1)
    return cur

def get_settlement_trading_day(buy_date_val: Any) -> Tuple[date, str]:
    """
    Xác định ngày T+2 (ngày về tài khoản chiều 13:00) theo chu kỳ T+2.5:
    - Nếu mua trong phiên giao dịch (hoặc trước 15:00 ngày giao dịch): Ngày T0 là ngày mua.
    - Nếu mua ngoài giờ (sau 15:00 hoặc ngày nghỉ): Ngày T0 là ngày giao dịch tiếp theo.
    - Ngày T+1: Ngày giao dịch thứ 1 sau T0.
    - Ngày T+2: Ngày giao dịch thứ 2 sau T0 (Khả dụng lúc 13:00).
    """
    buy_dt = parse_vietnam_datetime(buy_date_val)
    buy_d = buy_dt.date()
    
    # Xác định ngày khớp T0
    if is_vietnam_trading_day(buy_dt) and buy_dt.hour < 15:
        t0_date = buy_d
    else:
        t0_date = get_next_trading_day(buy_d) if buy_dt.hour >= 15 or not is_vietnam_trading_day(buy_dt) else buy_d
    
    t1_date = get_next_trading_day(t0_date)
    t2_date = get_next_trading_day(t1_date)
    
    desc = f"{t2_date.strftime('%d/%m/%Y')} (Phiên Chiều từ 13:00)"
    return t2_date, desc

def calculate_t_plus_status(buy_date_val: Any, current_dt: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Tính toán trạng thái chu kỳ T+ của sàn chứng khoán Việt Nam (Quy chế T+2.5):
    - Chu kỳ T tính theo các NGÀY GIAO DỊCH THỰC TẾ (bỏ qua Thứ Bảy, Chủ Nhật và ngày Lễ/Tết).
    - Ngày mua: T+0 (Chưa khả dụng)
    - 1 ngày giao dịch sau ngày mua: T+1 (Chưa khả dụng)
    - 2 ngày giao dịch sau ngày mua:
      + Trước 13:00 (Phiên Sáng & Nghỉ trưa): T+2 Sáng (Chưa khả dụng - Chờ về)
      + Từ 13:00 trở đi (Phiên Chiều): T+2.5 (KHẢ DỤNG GIAO DỊCH - Bắt đầu được bán)
    - Từ ngày giao dịch thứ 3 trở đi: Đã đủ T+ (KHẢ DỤNG GIAO DỊCH)
    """
    if current_dt is None:
        current_dt = datetime.now(VIETNAM_TZ)
    elif current_dt.tzinfo is None:
        current_dt = current_dt.replace(tzinfo=VIETNAM_TZ)
    else:
        current_dt = current_dt.astimezone(VIETNAM_TZ)

    buy_dt = parse_vietnam_datetime(buy_date_val)
    t2_date, t2_desc = get_settlement_trading_day(buy_date_val)
    curr_d = current_dt.date()

    buy_d = buy_dt.date()
    if is_vietnam_trading_day(buy_dt) and buy_dt.hour < 15:
        t0_date = buy_d
    else:
        t0_date = get_next_trading_day(buy_d) if buy_dt.hour >= 15 or not is_vietnam_trading_day(buy_dt) else buy_d

    if curr_d < t0_date:
        t_days = 0
    else:
        t_days = 0
        cur = t0_date + timedelta(days=1)
        while cur <= curr_d:
            if is_vietnam_trading_day(datetime(cur.year, cur.month, cur.day, tzinfo=VIETNAM_TZ)):
                t_days += 1
            cur += timedelta(days=1)

    if t_days == 0:
        return {
            "t_days": 0,
            "is_available": False,
            "status_code": "T0",
            "status_label": "Chờ về (T+0)",
            "badge": "⏳ T+0",
            "settlement_desc": t2_desc
        }
    elif t_days == 1:
        return {
            "t_days": 1,
            "is_available": False,
            "status_code": "T1",
            "status_label": "Chờ về (T+1)",
            "badge": "⏳ T+1",
            "settlement_desc": t2_desc
        }
    elif t_days == 2:
        if curr_d == t2_date and current_dt.hour < 13:
            return {
                "t_days": 2,
                "is_available": False,
                "status_code": "T2_MORNING",
                "status_label": "Chờ về (T+2 Sáng)",
                "badge": "⏳ T+2 Sáng",
                "settlement_desc": t2_desc
            }
        else:
            return {
                "t_days": 2,
                "is_available": True,
                "status_code": "T2_AFTERNOON",
                "status_label": "Khả dụng (T+2.5)",
                "badge": "✅ Khả dụng",
                "settlement_desc": "Đã về tài khoản"
            }
    else:
        return {
            "t_days": t_days,
            "is_available": True,
            "status_code": "READY",
            "status_label": "Khả dụng",
            "badge": "✅ Khả dụng",
            "settlement_desc": "Đã về tài khoản"
        }

