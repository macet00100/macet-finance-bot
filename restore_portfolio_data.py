import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
DB_PATH = Path(__file__).resolve().parent / "finance_bot.db"
VIETNAM_TZ = ZoneInfo("Asia/Bangkok")

POSITIONS_DATA = [
    {
        "symbol": "VHM",
        "shares": 1800,
        "buy_price": 62.25,
        "cost_basis": 112050000.0,
        "take_profit_price": 69.72,
        "take_profit_pct": 12.0,
        "stop_loss_price": 58.51,
        "stop_loss_pct": 6.0,
        "sector": "Bất động sản",
        "note": "Khớp lệnh giải ngân phiên 17/11/2026 (Giá TB 62.25)"
    },
    {
        "symbol": "VIC",
        "shares": 400,
        "buy_price": 246.10,
        "cost_basis": 98440000.0,
        "take_profit_price": 275.63,
        "take_profit_pct": 12.0,
        "stop_loss_price": 231.33,
        "stop_loss_pct": 6.0,
        "sector": "Bất động sản",
        "note": "Khớp lệnh giải ngân phiên 17/11/2026 (Giá TB 246.10)"
    },
    {
        "symbol": "MSR",
        "shares": 1500,
        "buy_price": 55.42,
        "cost_basis": 83130000.0,
        "take_profit_price": 62.07,
        "take_profit_pct": 12.0,
        "stop_loss_price": 52.09,
        "stop_loss_pct": 6.0,
        "sector": "Khai khoáng, Vật liệu",
        "note": "Khớp lệnh giải ngân phiên 17/11/2026 (Giá TB 55.42)"
    },
    {
        "symbol": "HDB",
        "shares": 3300,
        "buy_price": 22.30,
        "cost_basis": 73590000.0,
        "take_profit_price": 24.98,
        "take_profit_pct": 12.0,
        "stop_loss_price": 20.96,
        "stop_loss_pct": 6.0,
        "sector": "Ngân hàng",
        "note": "Khớp lệnh giải ngân phiên 17/11/2026"
    },
    {
        "symbol": "SSI",
        "shares": 3000,
        "buy_price": 19.90,
        "cost_basis": 59700000.0,
        "take_profit_price": 22.29,
        "take_profit_pct": 12.0,
        "stop_loss_price": 18.71,
        "stop_loss_pct": 6.0,
        "sector": "Chứng khoán",
        "note": "Khớp lệnh giải ngân phiên 17/11/2026"
    },
    {
        "symbol": "TCH",
        "shares": 4500,
        "buy_price": 13.15,
        "cost_basis": 59175000.0,
        "take_profit_price": 14.73,
        "take_profit_pct": 12.0,
        "stop_loss_price": 12.36,
        "stop_loss_pct": 6.0,
        "sector": "Bất động sản",
        "note": "Khớp lệnh giải ngân phiên 17/11/2026"
    },
    {
        "symbol": "GMD",
        "shares": 900,
        "buy_price": 53.30,
        "cost_basis": 47970000.0,
        "take_profit_price": 59.70,
        "take_profit_pct": 12.0,
        "stop_loss_price": 50.10,
        "stop_loss_pct": 6.0,
        "sector": "Cảng biển",
        "note": "Khớp lệnh giải ngân phiên 17/11/2026"
    },
    {
        "symbol": "PVS",
        "shares": 1700,
        "buy_price": 28.00,
        "cost_basis": 47600000.0,
        "take_profit_price": 31.36,
        "take_profit_pct": 12.0,
        "stop_loss_price": 26.32,
        "stop_loss_pct": 6.0,
        "sector": "Dầu khí",
        "note": "Khớp lệnh giải ngân phiên 17/11/2026"
    },
    {
        "symbol": "HVN",
        "shares": 1800,
        "buy_price": 22.10,
        "cost_basis": 39780000.0,
        "take_profit_price": 24.75,
        "take_profit_pct": 12.0,
        "stop_loss_price": 20.77,
        "stop_loss_pct": 6.0,
        "sector": "Hàng không",
        "note": "Khớp lệnh giải ngân phiên 17/11/2026"
    },
    {
        "symbol": "VNM",
        "shares": 700,
        "buy_price": 53.70,
        "cost_basis": 37590000.0,
        "take_profit_price": 60.14,
        "take_profit_pct": 12.0,
        "stop_loss_price": 50.48,
        "stop_loss_pct": 6.0,
        "sector": "Bán lẻ",
        "note": "Khớp lệnh giải ngân phiên 17/11/2026"
    },
    {
        "symbol": "KBC",
        "shares": 1400,
        "buy_price": 26.80,
        "cost_basis": 37520000.0,
        "take_profit_price": 30.02,
        "take_profit_pct": 12.0,
        "stop_loss_price": 25.19,
        "stop_loss_pct": 6.0,
        "sector": "Khu công nghiệp",
        "note": "Khớp lệnh giải ngân phiên 17/11/2026"
    },
    {
        "symbol": "VGI",
        "shares": 500,
        "buy_price": 72.20,
        "cost_basis": 36100000.0,
        "take_profit_price": 80.86,
        "take_profit_pct": 12.0,
        "stop_loss_price": 67.87,
        "stop_loss_pct": 6.0,
        "sector": "Viễn thông",
        "note": "Khớp lệnh giải ngân phiên 17/11/2026"
    },
    {
        "symbol": "MSN",
        "shares": 500,
        "buy_price": 71.50,
        "cost_basis": 35750000.0,
        "take_profit_price": 80.08,
        "take_profit_pct": 12.0,
        "stop_loss_price": 67.21,
        "stop_loss_pct": 6.0,
        "sector": "Bán lẻ",
        "note": "Khớp lệnh giải ngân phiên 17/11/2026"
    },
    {
        "symbol": "CTR",
        "shares": 600,
        "buy_price": 59.50,
        "cost_basis": 35700000.0,
        "take_profit_price": 66.64,
        "take_profit_pct": 12.0,
        "stop_loss_price": 55.93,
        "stop_loss_pct": 6.0,
        "sector": "Hạ tầng viễn thông",
        "note": "Khớp lệnh giải ngân phiên 17/11/2026"
    },
    {
        "symbol": "VHC",
        "shares": 700,
        "buy_price": 50.70,
        "cost_basis": 35490000.0,
        "take_profit_price": 56.78,
        "take_profit_pct": 12.0,
        "stop_loss_price": 47.66,
        "stop_loss_pct": 6.0,
        "sector": "Thủy sản",
        "note": "Khớp lệnh giải ngân phiên 17/11/2026"
    }
]

def restore_15_positions(target_db_path: Path = DB_PATH) -> dict:
    """Khôi phục lại toàn bộ 15 vị thế cổ phiếu và số dư tiền mặt 168.405.000 VNĐ"""
    conn = sqlite3.connect(target_db_path)
    cursor = conn.cursor()

    # 1. Đảm bảo bảng portfolio_positions có cột sector
    cursor.execute("PRAGMA table_info(portfolio_positions)")
    existing_cols = [c[1] for c in cursor.fetchall()]
    if "sector" not in existing_cols:
        cursor.execute("ALTER TABLE portfolio_positions ADD COLUMN sector TEXT DEFAULT ''")

    # 2. Xóa các vị thế OPEN cũ để tránh trùng lặp
    cursor.execute("DELETE FROM portfolio_positions WHERE status = 'OPEN'")

    # 3. Nạp lại 15 vị thế thực tế
    now_vn = datetime.now(VIETNAM_TZ).strftime("%Y-%m-%d %H:%M:%S")
    for pos in POSITIONS_DATA:
        cursor.execute("""
            INSERT INTO portfolio_positions (
                symbol, shares, buy_price, cost_basis,
                take_profit_price, take_profit_pct,
                stop_loss_price, stop_loss_pct,
                status, buy_date, sector, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?, ?)
        """, (
            pos["symbol"],
            pos["shares"],
            pos["buy_price"],
            pos["cost_basis"],
            pos["take_profit_price"],
            pos["take_profit_pct"],
            pos["stop_loss_price"],
            pos["stop_loss_pct"],
            now_vn,
            pos["sector"],
            pos["note"]
        ))

    # 4. Cập nhật số dư tài khoản tiền mặt chính xác
    # Tiền mặt: 168,405,000 VNĐ
    CASH_BALANCE = 168405000.0
    cursor.execute("""
        INSERT INTO portfolio_account (id, initial_capital, cash_balance, updated_at)
        VALUES (1, 1000000000.0, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            cash_balance = excluded.cash_balance,
            updated_at = CURRENT_TIMESTAMP
    """, (CASH_BALANCE,))

    conn.commit()
    conn.close()

    total_cost = sum(p["cost_basis"] for p in POSITIONS_DATA)
    logger.info(f"Đã khôi phục thành công 15 vị thế cổ phiếu (Tổng giá vốn: {total_cost:,.0f} đ, Tiền mặt: {CASH_BALANCE:,.0f} đ)!")
    return {
        "status": "success",
        "positions_count": len(POSITIONS_DATA),
        "total_cost_basis": total_cost,
        "cash_balance": CASH_BALANCE,
        "symbols": [p["symbol"] for p in POSITIONS_DATA]
    }

if __name__ == "__main__":
    res = restore_15_positions()
    print("Restore result:", res)
