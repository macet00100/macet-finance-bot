import asyncio
import logging
import io
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, Tuple
from aiogram import Bot
from aiogram.types import BufferedInputFile
from aiogram.enums import ParseMode

import config
import db
import holiday_checker
import portfolio_manager
import table_image_generator

logger = logging.getLogger(__name__)
VIETNAM_TZ = ZoneInfo("Asia/Bangkok")

WEEKDAYS_VN = {
    0: "Thứ Hai",
    1: "Thứ Ba",
    2: "Thứ Tư",
    3: "Thứ Năm",
    4: "Thứ Sáu",
    5: "Thứ Bảy",
    6: "Chủ Nhật"
}

def generate_closing_portfolio_assets() -> Optional[Tuple[io.BytesIO, str]]:
    """Tạo ảnh bảng danh mục và caption tổng quan"""
    now = datetime.now(VIETNAM_TZ)
    weekday_name = WEEKDAYS_VN.get(now.weekday(), "Thứ Hai")
    date_display = f"{weekday_name}, ngày {now.strftime('%d/%m/%Y')} (Kết phiên 15:30)"

    summary = portfolio_manager.get_portfolio_summary()
    initial_cap = summary["initial_capital"]
    total_assets = summary["total_assets"]
    cash = summary["cash_balance"]
    stock_val = summary["stock_value"]
    pnl_total = summary["pnl_total"]
    pnl_pct = summary["pnl_total_pct"]
    positions = summary["positions"]

    # Render ảnh bảng biểu chia hàng chia cột
    img_buf = table_image_generator.render_portfolio_table_image(summary, date_display)
    if not img_buf:
        return None

    icon_pnl = "🟢" if pnl_total >= 0 else "🔴"
    sign_pnl = "+" if pnl_total >= 0 else ""

    caption = (
        "📊 **BẢNG TỔNG KẾT DANH MỤC ĐẦU TƯ CUỐI PHIÊN | MACET FINANCE**\n"
        f"📅 *{date_display}*\n\n"
        f"💵 **Tài sản gốc (Vốn ban đầu):** `{initial_cap:,.0f} VNĐ`\n"
        f"💰 **Tổng tài sản hiện tại:** `{total_assets:,.0f} VNĐ`\n"
        f"{icon_pnl} **Tổng lãi/lỗ:** `{sign_pnl}{pnl_total:,.0f} VNĐ` (`{sign_pnl}{pnl_pct:.2f}%`)\n"
        f"💵 **Tiền mặt:** `{cash:,.0f} VNĐ` ({(cash/total_assets)*100:.1f}%) | "
        f"📦 **Cổ phiếu:** `{stock_val:,.0f} VNĐ` ({(stock_val/total_assets)*100:.1f}%)\n\n"
        "📌 *Chi tiết từng mã, số lượng, tỷ trọng % tài sản, lãi/lỗ và ngưỡng TP/SL được tổng hợp trực quan trong ảnh bảng biểu phía trên.*\n\n"
        "──────────────────\n"
        f"📢 **Macet Finance Research** | Báo cáo danh mục định kỳ 15:30 mỗi ngày giao dịch."
    )

    return img_buf, caption

async def broadcast_closing_portfolio(bot: Bot, force: bool = False) -> bool:
    """
    Phát sóng Bảng danh mục đầu tư cuối phiên (15:30) dưới dạng ẢNH BẢNG BIỂU chia hàng chia cột lên Kênh:
    - Tự động bỏ qua Thứ 7, Chủ Nhật và ngày lễ.
    - Đảm bảo mỗi ngày chỉ phát sóng 1 lần.
    """
    now = datetime.now(VIETNAM_TZ)
    today_str = now.strftime("%Y-%m-%d")

    if not force:
        if not holiday_checker.is_vietnam_trading_day(now):
            logger.info(f"Hôm nay ({today_str}) là ngày nghỉ sàn chứng khoán. Bỏ qua bảng danh mục 15:30.")
            return False

        if portfolio_manager.is_closing_report_sent_today(today_str):
            logger.info(f"Bảng danh mục cuối phiên ngày {today_str} đã được đăng trước đó. Bỏ qua.")
            return False

    logger.info(f"Bắt đầu khởi tạo Bảng danh mục dạng ảnh cuối phiên 15:30 ngày {today_str}...")
    assets = generate_closing_portfolio_assets()
    if not assets:
        logger.error("Không tạo được ảnh bảng danh mục cuối phiên.")
        return False

    img_buf, caption = assets

    try:
        photo = BufferedInputFile(img_buf.getvalue(), filename=f"portfolio_closing_{today_str}.png")
        sent_msg = await bot.send_photo(
            chat_id=config.TELEGRAM_CHANNEL_ID,
            photo=photo,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"Đã phát sóng Bảng danh mục DẠNG ẢNH ngày {today_str} lên Kênh thành công (ID {sent_msg.message_id})!")

        # Tự động ghim bảng tổng kết danh mục lên đầu Kênh Telegram
        try:
            await bot.pin_chat_message(
                chat_id=config.TELEGRAM_CHANNEL_ID,
                message_id=sent_msg.message_id,
                disable_notification=False
            )
            logger.info(f"Đã GHIM bảng danh mục cuối phiên ID {sent_msg.message_id} lên đầu Kênh Telegram thành công!")
        except Exception as pin_err:
            logger.warning(f"Lỗi khi ghim tin nhắn bảng danh mục ID {sent_msg.message_id}: {pin_err}")

        portfolio_manager.mark_closing_report_sent_today(today_str)
        return True
    except Exception as e:
        logger.error(f"Lỗi khi gửi ảnh bảng danh mục cuối phiên: {e}")
        return False
