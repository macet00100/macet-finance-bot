import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
DB_PATH = Path(__file__).resolve().parent / "finance_bot.db"

def reset_entire_database():
    """Xóa toàn bộ dữ liệu giao dịch, vị thế, tin tức cũ và nạp lại 1 tỷ vốn ban đầu"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Reset tài khoản về 1 Tỷ đồng tiền mặt nguyên vẹn
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_account (
            id INTEGER PRIMARY KEY,
            initial_capital REAL DEFAULT 1000000000.0,
            cash_balance REAL DEFAULT 1000000000.0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("DELETE FROM portfolio_account")
    cursor.execute(
        "INSERT INTO portfolio_account (id, initial_capital, cash_balance) VALUES (1, 1000000000.0, 1000000000.0)"
    )

    # 2. Xóa sạch các vị thế mở và đã đóng
    cursor.execute("DELETE FROM portfolio_positions")

    # 3. Xóa sạch lịch sử giao dịch
    cursor.execute("DELETE FROM portfolio_transactions")

    # 4. Xóa lịch sử báo cáo cuối phiên & bản tin vĩ mô để bắt đầu chu kỳ mới
    cursor.execute("DELETE FROM daily_closing_reports")
    cursor.execute("DELETE FROM daily_macro_history")

    # 5. Xóa danh sách lệnh chờ
    cursor.execute("DELETE FROM pending_orders")

    # 6. Xóa danh sách tin đã publish để quét lại hoặc chuẩn bị cho các tin tức tiếp theo
    cursor.execute("DELETE FROM published_news")

    conn.commit()
    cursor.execute("VACUUM")
    conn.close()
    print("✅ ĐÃ RESET TOÀN BỘ DATABASE VỀ 1 TỶ TIỀN MẶT NGUYÊN VẸN!")

if __name__ == "__main__":
    reset_entire_database()
