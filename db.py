import sqlite3
import re
from pathlib import Path
from typing import List, Dict, Any

DB_PATH = Path(__file__).resolve().parent / "finance_bot.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    """Khởi tạo các bảng dữ liệu cần thiết"""
    with get_connection() as conn:
        cursor = conn.cursor()
        # Bảng lưu tin tức đã đăng lên kênh để tránh đăng trùng
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS published_news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                news_id TEXT UNIQUE,
                title TEXT,
                published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Bảng lưu lịch sử bản tin vĩ mô đầu ngày (mỗi ngày 1 bản tin)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_macro_history (
                date_str TEXT PRIMARY KEY,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Bảng watchlist lưu các mã người dùng theo dõi
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                symbol TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, symbol)
            )
        """)
        # Bảng lưu nhóm ngành ưu tiên vĩ mô (Top-Down Macro Priorities)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS macro_sector_priorities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sector_name TEXT NOT NULL,
                priority_level TEXT DEFAULT 'HIGH',
                catalyst TEXT,
                favored_tickers TEXT,
                updated_date TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        # Bảng lưu các lệnh chờ khớp khi thị trường mở phiên thực tế (Pending Orders)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                target_amount REAL DEFAULT 0,
                planned_price REAL DEFAULT 0,
                sector TEXT,
                tp_pct REAL DEFAULT 12.0,
                sl_pct REAL DEFAULT 6.0,
                note TEXT,
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                executed_at TIMESTAMP,
                executed_price REAL,
                executed_shares INTEGER
            )
        """)
        conn.commit()

def is_news_published(news_id: str, title: str = "") -> bool:
    """Kiểm tra tin tức đã được đăng lên kênh chưa (theo cả URL và Tiêu đề bài viết)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        # 1. Kiểm tra theo news_id (URL bài viết)
        cursor.execute("SELECT 1 FROM published_news WHERE news_id = ?", (news_id,))
        if cursor.fetchone() is not None:
            return True
        # 2. Kiểm tra theo tiêu đề (tránh trường hợp cùng 1 bài xuất hiện ở nhiều feed RSS khác URL)
        if title:
            clean_title = re.sub(r"\s+", " ", title).strip().lower()
            cursor.execute("SELECT 1 FROM published_news WHERE LOWER(TRIM(title)) = ?", (clean_title,))
            if cursor.fetchone() is not None:
                return True
        return False

def mark_news_published(news_id: str, title: str):
    """Đánh dấu tin tức đã đăng"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO published_news (news_id, title) VALUES (?, ?)",
            (news_id, title)
        )
        conn.commit()

def is_macro_sent_today(date_str: str) -> bool:
    """Kiểm tra bản tin vĩ mô ngày date_str đã được đăng chưa"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM daily_macro_history WHERE date_str = ?", (date_str,))
        return cursor.fetchone() is not None

def mark_macro_sent_today(date_str: str):
    """Đánh dấu bản tin vĩ mô ngày date_str đã được đăng"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO daily_macro_history (date_str) VALUES (?)",
            (date_str,)
        )
        conn.commit()

def set_macro_priority_sectors(sectors_data: List[Dict[str, Any]], date_str: str):
    """Cập nhật danh sách các nhóm ngành ưu tiên vĩ mô"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE macro_sector_priorities SET is_active = 0")
        for s in sectors_data:
            cursor.execute("""
                INSERT INTO macro_sector_priorities (
                    sector_name, priority_level, catalyst, favored_tickers, updated_date, is_active
                ) VALUES (?, ?, ?, ?, ?, 1)
            """, (
                s.get("sector_name", "").strip(),
                s.get("priority_level", "HIGH"),
                s.get("catalyst", "").strip(),
                s.get("favored_tickers", "").strip(),
                date_str
            ))
        conn.commit()

def get_active_priority_sectors() -> List[Dict[str, Any]]:
    """Lấy danh sách các nhóm ngành ưu tiên vĩ mô đang hoạt động"""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM macro_sector_priorities WHERE is_active = 1")
        return [dict(r) for r in cursor.fetchall()]

def check_stock_sector_priority(ticker: str, sector: str):
    """
    Kiểm tra xem mã cổ phiếu hoặc ngành có nằm trong danh sách ưu tiên vĩ mô không
    Trả về: (is_priority, sector_info_dict)
    """
    priorities = get_active_priority_sectors()
    ticker_clean = (ticker or "").strip().upper()
    sector_clean = (sector or "").strip().lower()

    for p in priorities:
        p_sec = p["sector_name"].strip().lower()
        p_tickers = [t.strip().upper() for t in p["favored_tickers"].replace(";", ",").split(",") if t.strip()]

        # 1. Khớp mã cổ phiếu trực tiếp
        if ticker_clean and ticker_clean in p_tickers:
            return True, p
        # 2. Khớp theo ngành
        if sector_clean and (p_sec in sector_clean or sector_clean in p_sec):
            return True, p

    return False, None

def add_pending_order(
    symbol: str,
    action: str,
    target_amount: float,
    planned_price: float,
    sector: str = "",
    tp_pct: float = 12.0,
    sl_pct: float = 6.0,
    note: str = ""
) -> int:
    """Thêm một lệnh vào hàng đợi chờ mở phiên giao dịch thực tế"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pending_orders (
                symbol, action, target_amount, planned_price, sector, tp_pct, sl_pct, note, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
        """, (symbol.strip().upper(), action, target_amount, planned_price, sector, tp_pct, sl_pct, note))
        conn.commit()
        return cursor.lastrowid

def get_pending_orders() -> List[Dict[str, Any]]:
    """Lấy danh sách các lệnh đang chờ khớp khi mở phiên"""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pending_orders WHERE status = 'PENDING' ORDER BY id ASC")
        return [dict(r) for r in cursor.fetchall()]

def mark_order_executed(order_id: int, executed_price: float, executed_shares: int):
    """Đánh dấu lệnh chờ đã được khớp thành công"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE pending_orders SET
                status = 'EXECUTED',
                executed_at = CURRENT_TIMESTAMP,
                executed_price = ?,
                executed_shares = ?
            WHERE id = ?
        """, (executed_price, executed_shares, order_id))
        conn.commit()

def mark_order_cancelled(order_id: int, reason: str = ""):
    """Hủy lệnh chờ"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE pending_orders SET
                status = 'CANCELLED',
                executed_at = CURRENT_TIMESTAMP,
                note = COALESCE(note, '') || ' | Hủy lệnh: ' || ?
            WHERE id = ?
        """, (reason, order_id))
        conn.commit()
