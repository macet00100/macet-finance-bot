import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from aiogram import Bot
from aiogram.enums import ParseMode

import config
import holiday_checker
import portfolio_manager
import data_fetcher

logger = logging.getLogger(__name__)
VIETNAM_TZ = ZoneInfo("Asia/Bangkok")

async def check_portfolio_triggers(bot: Bot) -> int:
    """
    Kiểm tra toàn bộ các mã đang nắm giữ trong danh mục:
    - CHỈ THỰC HIỆN TRONG GIỜ GIAO DỊCH THỰC TẾ (is_market_open == True).
    - Tự động bỏ qua giờ nghỉ trưa (11:30 - 13:00) và ngoài giờ giao dịch.
    - Nếu chạm giá chốt lời: Tự động bán chốt lãi và bắn thông báo lên Kênh.
    - Nếu chạm giá cắt lỗ: Tự động bán cắt lỗ kỷ luật và bắn thông báo lên Kênh.
    Trả về số lệnh đã kích hoạt bán.
    """
    now = datetime.now(VIETNAM_TZ)
    if not holiday_checker.is_market_open(now):
        return 0

    positions = portfolio_manager.get_open_positions()
    if not positions:
        return 0

    triggered_count = 0

    for pos in positions:
        sym = pos["symbol"]
        pos_id = pos["id"]
        buy_price = pos["buy_price"]
        shares = pos["shares"]
        tp_price = pos["take_profit_price"]
        sl_price = pos["stop_loss_price"]

        # Lấy giá thị trường mới nhất
        df = data_fetcher.get_stock_history(sym, days=5)
        if df is None or len(df) == 0:
            continue

        current_price = float(df["Close"].iloc[-1])

        # 1. Kích hoạt Chốt lãi
        if tp_price and current_price >= tp_price:
            sell_res = portfolio_manager.sell_stock(pos_id, current_price, reason="CHỐT LÃI MỤC TIÊU")
            if sell_res:
                triggered_count += 1
                new_summary = portfolio_manager.get_portfolio_summary()
                msg = (
                    "🎯 **TÍN HIỆU DANH MỤC: ĐẠT MỤC TIÊU CHỐT LÃI | MACET FINANCE**\n\n"
                    f"🏆 **Cổ phiếu:** #{sym} ({shares:,} cp)\n"
                    f"💵 **Giá mua:** `{buy_price:,.2f}` ➔ **Giá khớp bán:** `{current_price:,.2f}`\n"
                    f"💰 **Lợi nhuận:** `+{sell_res['pnl_amount']:,.0f} VNĐ` (`+{sell_res['pnl_pct']:.2f}%`)\n"
                    f"📈 **Quyết định:** Hiện thực hóa lợi nhuận toàn phần, thu hồi vốn tiền mặt chờ cơ hội mới.\n\n"
                    f"💰 **Tổng tài sản quỹ:** `{new_summary['total_assets']:,.0f} VNĐ` "
                    f"(Tiền mặt: `{new_summary['cash_balance']:,.0f} VNĐ` | Lãi ròng: `{new_summary['pnl_total']:+,.0f} VNĐ`)\n"
                    "──────────────────\n"
                    f"📢 **Macet Finance Research**"
                )
                try:
                    await bot.send_message(
                        chat_id=config.TELEGRAM_CHANNEL_ID,
                        text=msg,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    logger.info(f"Đã phát sóng thông báo CHỐT LÃI #{sym} lên kênh")
                except Exception as e:
                    logger.error(f"Lỗi gửi thông báo chốt lãi #{sym}: {e}")

        # 2. Kích hoạt Cắt lỗ
        elif sl_price and current_price <= sl_price:
            sell_res = portfolio_manager.sell_stock(pos_id, current_price, reason="CẮT LỖ KỶ LUẬT")
            if sell_res:
                triggered_count += 1
                new_summary = portfolio_manager.get_portfolio_summary()
                msg = (
                    "🛡️ **TÍN HIỆU DANH MỤC: KÍCH HOẠT CẮT LỖ KỶ LUẬT | MACET FINANCE**\n\n"
                    f"⚠️ **Cổ phiếu:** #{sym} ({shares:,} cp)\n"
                    f"💵 **Giá mua:** `{buy_price:,.2f}` ➔ **Giá khớp bán:** `{current_price:,.2f}`\n"
                    f"🔻 **Mức lỗ:** `{sell_res['pnl_amount']:,.0f} VNĐ` (`{sell_res['pnl_pct']:.2f}%`)\n"
                    f"🛡️ **Quyết định:** Bán cắt lỗ kỷ luật để bảo vệ nguồn vốn, đưa vào danh sách theo dõi thêm.\n\n"
                    f"💰 **Tổng tài sản quỹ:** `{new_summary['total_assets']:,.0f} VNĐ` "
                    f"(Tiền mặt: `{new_summary['cash_balance']:,.0f} VNĐ`)\n"
                    "──────────────────\n"
                    f"📢 **Macet Finance Research**"
                )
                try:
                    await bot.send_message(
                        chat_id=config.TELEGRAM_CHANNEL_ID,
                        text=msg,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    logger.info(f"Đã phát sóng thông báo CẮT LỖ #{sym} lên kênh")
                except Exception as e:
                    logger.error(f"Lỗi gửi thông báo cắt lỗ #{sym}: {e}")

    return triggered_count
