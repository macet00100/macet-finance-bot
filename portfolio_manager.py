import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from zoneinfo import ZoneInfo
import data_fetcher

logger = logging.getLogger(__name__)
VIETNAM_TZ = ZoneInfo("Asia/Bangkok")
DB_PATH = Path(__file__).resolve().parent / "finance_bot.db"
INITIAL_CAPITAL = 1_000_000_000.0  # 1 Tỷ đồng

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_portfolio_db():
    """Khởi tạo tài khoản vốn 1 tỷ và bảng danh mục đầu tư"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Bảng tài khoản vốn
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_account (
                id INTEGER PRIMARY KEY,
                initial_capital REAL DEFAULT 1000000000.0,
                cash_balance REAL DEFAULT 1000000000.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Bảng các vị thế cổ phiếu đang nắm giữ hoặc đã đóng
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                shares INTEGER NOT NULL,
                buy_price REAL NOT NULL,
                cost_basis REAL NOT NULL,
                take_profit_price REAL,
                take_profit_pct REAL,
                stop_loss_price REAL,
                stop_loss_pct REAL,
                status TEXT DEFAULT 'OPEN',
                buy_date TEXT,
                close_date TEXT,
                close_price REAL,
                pnl_amount REAL DEFAULT 0,
                pnl_pct REAL DEFAULT 0,
                sector TEXT DEFAULT '',
                note TEXT
            )
        """)
        # Kiểm tra và thêm cột sector nếu chưa có
        cursor.execute("PRAGMA table_info(portfolio_positions)")
        existing_cols = [c[1] for c in cursor.fetchall()]
        if "sector" not in existing_cols:
            cursor.execute("ALTER TABLE portfolio_positions ADD COLUMN sector TEXT DEFAULT ''")

        # Bảng lịch sử giao dịch mua/bán
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                shares INTEGER NOT NULL,
                price REAL NOT NULL,
                total_value REAL NOT NULL,
                pnl_amount REAL DEFAULT 0,
                pnl_pct REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                note TEXT
            )
        """)

        # Bảng lịch sử báo cáo tổng kết cuối phiên 15:30
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_closing_reports (
                date_str TEXT PRIMARY KEY,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tạo tài khoản ban đầu nếu chưa tồn tại
        cursor.execute("SELECT id FROM portfolio_account WHERE id = 1")
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO portfolio_account (id, initial_capital, cash_balance) VALUES (1, ?, ?)",
                (INITIAL_CAPITAL, INITIAL_CAPITAL)
            )
        conn.commit()

def is_closing_report_sent_today(date_str: str) -> bool:
    """Kiểm tra báo cáo cuối phiên ngày date_str đã được đăng chưa"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM daily_closing_reports WHERE date_str = ?", (date_str,))
        return cursor.fetchone() is not None

def mark_closing_report_sent_today(date_str: str):
    """Đánh dấu báo cáo cuối phiên ngày date_str đã được đăng"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO daily_closing_reports (date_str) VALUES (?)",
            (date_str,)
        )
        conn.commit()

def get_cash_balance() -> float:
    """Lấy số dư tiền mặt hiện tại"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT cash_balance FROM portfolio_account WHERE id = 1")
        row = cursor.fetchone()
        return float(row[0]) if row else INITIAL_CAPITAL

def get_open_positions() -> List[Dict[str, Any]]:
    """Lấy danh sách các mã cổ phiếu đang mở vị thế (OPEN)"""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM portfolio_positions WHERE status = 'OPEN'")
        return [dict(row) for row in cursor.fetchall()]

def get_portfolio_summary() -> Dict[str, Any]:
    """
    Tính toán tổng quan danh mục:
    - Kéo thị giá hiện tại của các mã đang giữ
    - Tính tổng giá trị cổ phiếu, tổng tài sản, lãi/lỗ
    """
    cash = get_cash_balance()
    positions = get_open_positions()
    
    total_stock_value = 0.0
    detailed_positions = []

    for pos in positions:
        sym = pos["symbol"]
        shares = pos["shares"]
        buy_price = pos["buy_price"] # nghìn VNĐ
        cost = pos["cost_basis"]
        
        # Kéo giá hiện tại từ sàn
        current_price = buy_price
        df = data_fetcher.get_stock_history(sym, days=10)
        if df is not None and len(df) > 0:
            current_price = float(df["Close"].iloc[-1])

        current_val = shares * current_price * 1000.0
        total_stock_value += current_val
        pnl_val = current_val - cost
        pnl_pct = (pnl_val / cost) * 100.0 if cost > 0 else 0.0

        detailed_positions.append({
            "id": pos["id"],
            "symbol": sym,
            "shares": shares,
            "buy_price": buy_price,
            "current_price": current_price,
            "cost_basis": cost,
            "current_value": current_val,
            "pnl_amount": pnl_val,
            "pnl_pct": pnl_pct,
            "take_profit_price": pos["take_profit_price"],
            "take_profit_pct": pos["take_profit_pct"],
            "stop_loss_price": pos["stop_loss_price"],
            "stop_loss_pct": pos["stop_loss_pct"],
            "sector": pos["sector"] if ("sector" in pos.keys()) else "",
            "buy_date": pos["buy_date"]
        })

    total_assets = cash + total_stock_value
    pnl_total = total_assets - INITIAL_CAPITAL
    pnl_total_pct = (pnl_total / INITIAL_CAPITAL) * 100.0

    return {
        "initial_capital": INITIAL_CAPITAL,
        "cash_balance": cash,
        "stock_value": total_stock_value,
        "total_assets": total_assets,
        "pnl_total": pnl_total,
        "pnl_total_pct": pnl_total_pct,
        "positions": detailed_positions,
        "open_count": len(detailed_positions)
    }

def buy_stock(
    symbol: str,
    target_amount_vnd: float,
    current_price: float,
    tp_pct: float = 12.0,
    sl_pct: float = 6.0,
    sector: str = "",
    note: str = ""
) -> Optional[Dict[str, Any]]:
    """Thực hiện mua mới cổ phiếu"""
    symbol = symbol.strip().upper()
    cash = get_cash_balance()
    if cash < 10_000_000:
        logger.warning(f"Tiền mặt không đủ để giải ngân ({cash:,.0f} VNĐ)")
        return None

    invest_amount = min(target_amount_vnd, cash)
    price_vnd = current_price * 1000.0

    raw_shares = int(invest_amount // price_vnd)
    shares = (raw_shares // 100) * 100
    if shares <= 0:
        logger.warning(f"Số lượng cổ phiếu tính ra = 0 cho {symbol}")
        return None

    actual_cost = shares * price_vnd
    new_cash = cash - actual_cost

    tp_price = round(current_price * (1 + tp_pct / 100.0), 2)
    sl_price = round(current_price * (1 - sl_pct / 100.0), 2)
    now_str = datetime.now(VIETNAM_TZ).strftime("%d/%m/%Y %H:%M")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE portfolio_account SET cash_balance = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1", (new_cash,))
        cursor.execute("""
            INSERT INTO portfolio_positions (
                symbol, shares, buy_price, cost_basis,
                take_profit_price, take_profit_pct,
                stop_loss_price, stop_loss_pct,
                status, buy_date, sector, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?, ?)
        """, (symbol, shares, current_price, actual_cost, tp_price, tp_pct, sl_price, sl_pct, now_str, sector, note))
        
        pos_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO portfolio_transactions (
                symbol, action, shares, price, total_value, note
            ) VALUES (?, 'BUY', ?, ?, ?, ?)
        """, (symbol, shares, current_price, actual_cost, note))

        conn.commit()

    logger.info(f"Đã giải ngân mua #{symbol}: {shares:,} cp giá {current_price:,.2f} (Tổng: {actual_cost:,.0f} VNĐ)")
    return {
        "position_id": pos_id,
        "symbol": symbol,
        "shares": shares,
        "buy_price": current_price,
        "actual_cost": actual_cost,
        "new_cash": new_cash,
        "tp_price": tp_price,
        "tp_pct": tp_pct,
        "sl_price": sl_price,
        "sl_pct": sl_pct
    }

def buy_more_stock(
    symbol: str,
    target_amount_vnd: float,
    current_price: float,
    note: str = ""
) -> Optional[Dict[str, Any]]:
    """Mua thêm cổ phiếu đã có trong danh mục để gia tăng tỷ trọng"""
    symbol = symbol.strip().upper()
    cash = get_cash_balance()
    if cash < 10_000_000:
        return None

    pos = None
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM portfolio_positions WHERE symbol = ? AND status = 'OPEN'", (symbol,))
        pos = cursor.fetchone()

    if not pos:
        return buy_stock(symbol, target_amount_vnd, current_price, note=note)

    invest_amount = min(target_amount_vnd, cash)
    price_vnd = current_price * 1000.0
    add_shares = int((invest_amount // price_vnd) // 100) * 100
    if add_shares <= 0:
        return None

    actual_add_cost = add_shares * price_vnd
    new_cash = cash - actual_add_cost

    old_shares = pos["shares"]
    old_cost = pos["cost_basis"]
    new_total_shares = old_shares + add_shares
    new_total_cost = old_cost + actual_add_cost
    new_avg_buy_price = round(new_total_cost / (new_total_shares * 1000.0), 2)

    tp_pct = pos["take_profit_pct"] or 12.0
    sl_pct = pos["stop_loss_pct"] or 6.0
    new_tp_price = round(new_avg_buy_price * (1 + tp_pct / 100.0), 2)
    new_sl_price = round(new_avg_buy_price * (1 - sl_pct / 100.0), 2)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE portfolio_account SET cash_balance = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1", (new_cash,))
        cursor.execute("""
            UPDATE portfolio_positions SET
                shares = ?,
                buy_price = ?,
                cost_basis = ?,
                take_profit_price = ?,
                stop_loss_price = ?,
                note = COALESCE(note, '') || ' | Mua thêm: ' || ?
            WHERE id = ?
        """, (new_total_shares, new_avg_buy_price, new_total_cost, new_tp_price, new_sl_price, note, pos["id"]))

        cursor.execute("""
            INSERT INTO portfolio_transactions (
                symbol, action, shares, price, total_value, note
            ) VALUES (?, 'BUY_MORE', ?, ?, ?, ?)
        """, (symbol, add_shares, current_price, actual_add_cost, note))
        conn.commit()

    logger.info(f"Đã MUA THÊM #{symbol}: +{add_shares:,} cp, tổng mới: {new_total_shares:,} cp (Giá TB: {new_avg_buy_price:,.2f})")
    return {
        "symbol": symbol,
        "add_shares": add_shares,
        "add_cost": actual_add_cost,
        "new_total_shares": new_total_shares,
        "new_avg_price": new_avg_buy_price,
        "new_total_cost": new_total_cost,
        "new_tp_price": new_tp_price,
        "new_sl_price": new_sl_price,
        "new_cash": new_cash
    }

def sell_partial_stock(
    symbol: str,
    sell_ratio: float = 0.5,
    current_price: float = 0,
    note: str = ""
) -> Optional[Dict[str, Any]]:
    """Bán bớt một phần cổ phiếu đang nắm giữ để chốt lời từng phần hoặc hạ tỷ trọng"""
    symbol = symbol.strip().upper()
    pos = None
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM portfolio_positions WHERE symbol = ? AND status = 'OPEN'", (symbol,))
        pos = cursor.fetchone()

    if not pos:
        return None

    old_shares = pos["shares"]
    old_cost = pos["cost_basis"]
    
    sell_shares = int((old_shares * sell_ratio) // 100) * 100
    if sell_shares <= 0:
        return None
    if sell_shares >= old_shares:
        return sell_stock(pos["id"], current_price, reason=note or "BÁN TOÀN PHẦN")

    cost_per_share = old_cost / old_shares
    sold_cost = sell_shares * cost_per_share
    sell_val = sell_shares * current_price * 1000.0
    pnl_val = sell_val - sold_cost
    pnl_pct = (pnl_val / sold_cost) * 100.0 if sold_cost > 0 else 0.0

    rem_shares = old_shares - sell_shares
    rem_cost = old_cost - sold_cost

    cash = get_cash_balance()
    new_cash = cash + sell_val

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE portfolio_account SET cash_balance = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1", (new_cash,))
        cursor.execute("""
            UPDATE portfolio_positions SET
                shares = ?,
                cost_basis = ?,
                note = COALESCE(note, '') || ' | Bán bớt: ' || ?
            WHERE id = ?
        """, (rem_shares, rem_cost, f"{sell_shares:,} cp", pos["id"]))

        cursor.execute("""
            INSERT INTO portfolio_transactions (
                symbol, action, shares, price, total_value, pnl_amount, pnl_pct, note
            ) VALUES (?, 'SELL_PARTIAL', ?, ?, ?, ?, ?, ?)
        """, (symbol, sell_shares, current_price, sell_val, pnl_val, pnl_pct, note))
        conn.commit()

    logger.info(f"Đã BÁN BỚT #{symbol}: {sell_shares:,} cp, còn lại {rem_shares:,} cp | Thu về: {sell_val:,.0f} VNĐ (Lãi/lỗ: {pnl_val:+,.0f} VNĐ, {pnl_pct:+.2f}%)")
    return {
        "symbol": symbol,
        "sell_shares": sell_shares,
        "rem_shares": rem_shares,
        "sell_val": sell_val,
        "pnl_amount": pnl_val,
        "pnl_pct": pnl_pct,
        "rem_cost": rem_cost,
        "new_cash": new_cash
    }

def sell_stock(position_id: int, current_price: float, reason: str = "TAKE_PROFIT") -> Optional[Dict[str, Any]]:
    """Bán toàn phần đóng vị thế cổ phiếu"""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM portfolio_positions WHERE id = ? AND status = 'OPEN'", (position_id,))
        pos = cursor.fetchone()
        if not pos:
            return None

        symbol = pos["symbol"]
        shares = pos["shares"]
        cost = pos["cost_basis"]
        
        sell_val = shares * current_price * 1000.0
        pnl_val = sell_val - cost
        pnl_pct = (pnl_val / cost) * 100.0 if cost > 0 else 0.0

        cursor.execute("SELECT cash_balance FROM portfolio_account WHERE id = 1")
        current_cash = float(cursor.fetchone()[0])
        new_cash = current_cash + sell_val
        now_str = datetime.now(VIETNAM_TZ).strftime("%d/%m/%Y %H:%M")

        cursor.execute("UPDATE portfolio_account SET cash_balance = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1", (new_cash,))
        cursor.execute("""
            UPDATE portfolio_positions SET
                status = 'CLOSED',
                close_date = ?,
                close_price = ?,
                pnl_amount = ?,
                pnl_pct = ?,
                note = ?
            WHERE id = ?
        """, (now_str, current_price, pnl_val, pnl_pct, reason, position_id))

        action_name = "SELL_TP" if "PROFIT" in reason.upper() else ("SELL_SL" if "LOSS" in reason.upper() else "SELL_MANUAL")
        cursor.execute("""
            INSERT INTO portfolio_transactions (
                symbol, action, shares, price, total_value, pnl_amount, pnl_pct, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (symbol, action_name, shares, current_price, sell_val, pnl_val, pnl_pct, reason))

        conn.commit()

    logger.info(f"Đã BÁN TOÀN PHẦN #{symbol}: {shares:,} cp giá {current_price:,.2f} | PnL: {pnl_val:+,.0f} VNĐ ({pnl_pct:+.2f}%)")
    return {
        "symbol": symbol,
        "shares": shares,
        "sell_price": current_price,
        "sell_value": sell_val,
        "pnl_amount": pnl_val,
        "pnl_pct": pnl_pct,
        "reason": reason
    }
