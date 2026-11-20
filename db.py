import sqlite3
import re
import unicodedata
from pathlib import Path
from typing import List, Dict, Any

DB_PATH = Path(__file__).resolve().parent / "finance_bot.db"

def normalize_title(title: str) -> str:
    """Chuẩn hóa tiêu đề bài viết: Unicode NFC, bỏ dấu câu, chữ thường, bỏ khoảng trắng thừa"""
    if not title:
        return ""
    text = unicodedata.normalize("NFC", str(title))
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

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
                normalized_title TEXT,
                published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Đảm bảo cột normalized_title tồn tại nếu bảng đã tạo từ trước
        try:
            cursor.execute("ALTER TABLE published_news ADD COLUMN normalized_title TEXT")
        except sqlite3.OperationalError:
            pass
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_published_news_norm ON published_news(normalized_title)")
        
        # Tự động chuẩn hóa các tiêu đề cũ trong database nếu chưa có normalized_title
        rows_to_update = cursor.execute("SELECT id, title FROM published_news WHERE normalized_title IS NULL AND title IS NOT NULL").fetchall()
        for r_id, r_title in rows_to_update:
            cursor.execute("UPDATE published_news SET normalized_title = ? WHERE id = ?", (normalize_title(r_title), r_id))
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
    """Kiểm tra tin tức đã được đăng lên kênh chưa (theo URL, Tiêu đề chuẩn hóa, và Độ tương đồng từ khóa >= 75%)"""
    norm = normalize_title(title) if title else ""
    with get_connection() as conn:
        cursor = conn.cursor()
        # 1. Kiểm tra theo news_id (URL bài viết)
        if news_id:
            cursor.execute("SELECT 1 FROM published_news WHERE news_id = ?", (news_id.strip(),))
            if cursor.fetchone() is not None:
                return True
        # 2. Kiểm tra theo tiêu đề đã chuẩn hóa triệt để
        if norm:
            cursor.execute("SELECT 1 FROM published_news WHERE normalized_title = ?", (norm,))
            if cursor.fetchone() is not None:
                return True

            # 3. Kiểm tra độ tương đồng mờ (Fuzzy Similarity >= 75%) với các tin đăng gần đây
            # Ngăn chặn báo chí đổi nhẹ vài từ trong tít (VD: 'Chuyện chưa kể' thành 'Chuyện chưa từng kể')
            words_a = set(norm.split())
            if len(words_a) >= 5:
                cursor.execute("SELECT normalized_title FROM published_news ORDER BY id DESC LIMIT 150")
                recent_titles = cursor.fetchall()
                for (past_norm,) in recent_titles:
                    if not past_norm:
                        continue
                    words_b = set(past_norm.split())
                    if not words_b:
                        continue
                    inter = len(words_a & words_b)
                    similarity = inter / max(len(words_a), len(words_b))
                    if similarity >= 0.75:
                        return True
        return False

def mark_news_published(news_id: str, title: str):
    """Đánh dấu tin tức đã đăng (lưu cả URL và Tiêu đề đã chuẩn hóa)"""
    clean_id = news_id.strip() if news_id else None
    clean_title = title.strip() if title else ""
    norm = normalize_title(clean_title)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO published_news (news_id, title, normalized_title) VALUES (?, ?, ?)",
            (clean_id, clean_title, norm)
        )
        if norm and clean_id:
            cursor.execute(
                "UPDATE published_news SET normalized_title = ? WHERE news_id = ? AND (normalized_title IS NULL OR normalized_title = '')",
                (norm, clean_id)
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
