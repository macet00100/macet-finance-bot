import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict, Any
from aiogram import Bot
from aiogram.enums import ParseMode

import config
import db
import holiday_checker
import data_fetcher
import portfolio_manager

logger = logging.getLogger(__name__)
VIETNAM_TZ = ZoneInfo("Asia/Bangkok")

async def execute_pending_orders(bot: Bot) -> int:
    """
    Kiểm tra và thực hiện khớp lệnh cho các vị thế đã lên kế hoạch ngoài giờ giao dịch:
    - Chỉ thực hiện khi sàn chứng khoán Việt Nam ĐANG TRONG PHIÊN GIAO DỊCH THỰC TẾ (is_market_open == True).
    - Tự động bỏ qua giờ nghỉ trưa (11:30 - 13:00), sau 15:00, trước 09:00 và ngày nghỉ.
    - Sau khi khớp lệnh thành công, tự động bắn thông báo xác nhận lên Kênh Telegram.
    """
    now = datetime.now(VIETNAM_TZ)
    if not holiday_checker.is_market_open(now):
        return 0

    pending = db.get_pending_orders()
    if not pending:
        return 0

    session_name = holiday_checker.get_session_name(now)
    executed_items: List[Dict[str, Any]] = []

    for order in pending:
        order_id = order["id"]
        sym = order["symbol"]
        action = order["action"]
        target_amount = order["target_amount"]
        planned_price = order["planned_price"]
        sector = order.get("sector", "")
        tp_pct = order.get("tp_pct", 12.0)
        sl_pct = order.get("sl_pct", 6.0)

        # Lấy thị giá mới nhất khi sàn mở cửa
        df = data_fetcher.get_stock_history(sym, days=5)
        if df is None or len(df) == 0:
            continue
        current_price = float(df["Close"].iloc[-1])

        try:
            if action == "BUY":
                buy_res = portfolio_manager.buy_stock(
                    symbol=sym,
                    target_amount_vnd=target_amount,
                    current_price=current_price,
                    tp_pct=tp_pct,
                    sl_pct=sl_pct,
                    sector=sector,
                    note=f"Khớp lệnh đầu phiên {session_name} từ lệnh chờ #{order_id}"
                )
                if buy_res:
                    db.mark_order_executed(order_id, current_price, buy_res["shares"])
                    executed_items.append({
                        "symbol": sym,
                        "action": "Mua mới",
                        "shares": buy_res["shares"],
                        "price": current_price,
                        "cost": buy_res["actual_cost"],
                        "tp": buy_res["tp_price"],
                        "sl": buy_res["sl_price"]
                    })
                else:
                    db.mark_order_cancelled(order_id, "Không đủ tiền mặt hoặc khối lượng không hợp lệ")

            elif action == "BUY_MORE":
                buy_res = portfolio_manager.buy_more_stock(
                    symbol=sym,
                    target_amount_vnd=target_amount,
                    current_price=current_price,
                    note=f"Khớp Mua thêm đầu phiên {session_name} từ lệnh chờ #{order_id}"
                )
                if buy_res:
                    db.mark_order_executed(order_id, current_price, buy_res["add_shares"])
                    executed_items.append({
                        "symbol": sym,
                        "action": "Mua thêm",
                        "shares": buy_res["add_shares"],
                        "price": current_price,
                        "cost": buy_res["add_cost"],
                        "tp": buy_res["new_tp_price"],
                        "sl": buy_res["new_sl_price"]
                    })
                else:
                    db.mark_order_cancelled(order_id, "Không đủ điều kiện mua thêm")

            elif action == "SELL_PARTIAL":
                sell_res = portfolio_manager.sell_partial_stock(
                    symbol=sym,
                    sell_ratio=0.5,
                    current_price=current_price,
                    note=f"Khớp Bán bớt đầu phiên {session_name} từ lệnh chờ #{order_id}"
                )
                if sell_res:
                    db.mark_order_executed(order_id, current_price, sell_res["sell_shares"])
                    executed_items.append({
                        "symbol": sym,
                        "action": "Bán bớt 50%",
                        "shares": sell_res["sell_shares"],
                        "price": current_price,
                        "cost": sell_res["sell_val"],
                        "pnl": sell_res["pnl_amount"]
                    })
                else:
                    db.mark_order_cancelled(order_id, "Không tìm thấy vị thế để bán bớt")

            elif action == "SELL_FULL":
                positions = portfolio_manager.get_open_positions()
                pos = next((p for p in positions if p["symbol"] == sym), None)
                if pos:
                    sell_res = portfolio_manager.sell_stock(
                        pos["id"],
                        current_price,
                        reason=f"Khớp Bán toàn phần đầu phiên {session_name}"
                    )
                    if sell_res:
                        db.mark_order_executed(order_id, current_price, sell_res["shares"])
                        executed_items.append({
                            "symbol": sym,
                            "action": "Bán toàn phần",
                            "shares": sell_res["shares"],
                            "price": current_price,
                            "cost": sell_res["sell_value"],
                            "pnl": sell_res["pnl_amount"]
                        })
                else:
                    db.mark_order_cancelled(order_id, "Vị thế không tồn tại")

        except Exception as e:
            logger.error(f"Lỗi khi khớp lệnh chờ #{order_id} ({sym}): {e}")

    # Bắn thông báo khớp lệnh tổng hợp lên Kênh Telegram
    if executed_items:
        new_summary = portfolio_manager.get_portfolio_summary()
        now_str = now.strftime("%H:%M - %d/%m/%Y")
        
        lines = []
        for it in executed_items:
            if "pnl" in it:
                lines.append(f"• ✅ **#{it['symbol']}** ({it['action']}): `{it['shares']:,} cp` giá `{it['price']:,.2f}` (Thu về: `{it['cost']:,.0f} đ` | Lãi/Lỗ: `{it['pnl']:+,.0f} đ`)")
            else:
                lines.append(f"• ✅ **#{it['symbol']}** ({it['action']}): `{it['shares']:,} cp` giá `{it['price']:,.2f}` (Trị giá: `{it['cost']:,.0f} đ` | Mục tiêu: `{it['tp']:,.2f}`)")

        detail_text = "\n".join(lines)
        msg = (
            "🔔 **KÍCH HOẠT KHỚP LỆNH PHIÊN GIAO DỊCH | MACET FINANCE**\n"
            f"📅 *{session_name} ({now_str})*\n\n"
            "Thị trường đã vào phiên giao dịch chính thức. Hệ thống thực hiện khớp lệnh thực tế cho các vị thế đã lên kế hoạch:\n\n"
            f"{detail_text}\n\n"
            f"💰 **Tổng tài sản quỹ:** `{new_summary['total_assets']:,.0f} VNĐ`\n"
            f"(Tiền mặt: `{new_summary['cash_balance']:,.0f} VNĐ` | Cổ phiếu: `{new_summary['stock_value']:,.0f} VNĐ`)\n"
            "──────────────────\n"
            f"📢 **Macet Finance Research**"
        )
        try:
            await bot.send_message(
                chat_id=config.TELEGRAM_CHANNEL_ID,
                text=msg,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"Đã phát sóng thông báo khớp lệnh đầu phiên cho {len(executed_items)} lệnh.")
        except Exception as e:
            logger.error(f"Lỗi gửi thông báo khớp lệnh đầu phiên: {e}")

    return len(executed_items)
