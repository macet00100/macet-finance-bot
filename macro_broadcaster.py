import asyncio
import logging
import io
from datetime import datetime
from typing import Optional, Tuple
from zoneinfo import ZoneInfo
from aiogram import Bot
from aiogram.types import BufferedInputFile, ReplyParameters
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

import config
import db
import holiday_checker
import data_fetcher
import technical_analysis
import chart_generator
import ai_analyzer

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

def generate_morning_macro_content() -> Optional[Tuple[io.BytesIO, str, str]]:
    """
    Tạo nội dung Bản tin Vĩ mô đầu ngày (8h00 sáng):
    - Kéo dữ liệu VN-Index 120 phiên gần nhất từ VNDirect.
    - Vẽ biểu đồ nến kỹ thuật VN-Index.
    - Phân tích bối cảnh vĩ mô, kịch bản thị trường và các nhóm ngành bằng Gemini.
    Trả về: (chart_buf, part1, part2)
    """
    df = data_fetcher.get_stock_history("VNINDEX", days=120)
    if df is None or len(df) < 30:
        logger.error("Không lấy được dữ liệu nến VNINDEX")
        return None

    ta = technical_analysis.analyze_stock(df)
    chart_buf = chart_generator.generate_candlestick_chart(df, "VNINDEX", num_candles=60)
    if not ta or not chart_buf:
        return None

    # Lấy tin tức tổng hợp để AI nắm bối cảnh vĩ mô
    recent_news = data_fetcher.get_latest_news(limit=5)
    news_context = "\n".join([f"- {n['title']}" for n in recent_news])

    sma50_val = f"{ta.get('sma50'):,.2f}" if ta.get("sma50") else "Đang kiểm định"

    prompt = f"""
Bạn là Giám đốc Chiến lược Đầu tư tại Macet Finance. Hãy soạn Bản tin Vĩ mô Đầu ngày (Morning Briefing) lúc 8h00 sáng gửi nhà đầu tư chứng khoán Việt Nam:

DỮ LIỆU KỸ THUẬT VN-INDEX PHIÊN GẦN NHẤT:
- Điểm đóng cửa: {ta.get('last_close'):,.2f} điểm (Biến động: {ta.get('change_price'):+.2f} điểm, {ta.get('pct_change'):+.2f}%)
- MA20: {ta.get('sma20'):,.2f} | MA50: {sma50_val}
- Chỉ số RSI(14): {ta.get('rsi'):.1f}
- Thanh khoản: {ta.get('vol_ratio'):.1f}x so với trung bình 20 phiên
- Tín hiệu: {'; '.join(ta.get('signals', []))}

TIN TỨC BỐI CẢNH VĨ MÔ GẦN NHẤT:
{news_context}

QUY TẮC BẮT BUỘC:
- TUYỆT ĐỐI KHÔNG dùng từ "AI", "trí tuệ nhân tạo", "mô hình", "tự động".
- Viết bằng văn phong sắc sảo, tự tin, chuyên nghiệp của bản tin chiến lược đầu ngày từ các định chế tài chính lớn.
- BẮT BUỘC BẮT ĐẦU NGAY bằng "🌐 **Bối cảnh Vĩ mô & Quốc tế:**". TUYỆT ĐỐI KHÔNG mở đầu bằng lời chào hỏi (Chào quý nhà đầu tư, Kính gửi...).
- BẮT BUỘC phân tách kết quả thành 2 phần bằng dấu `===SPLIT===`:
- PHẦN 1 viết súc tích, cô đọng (tối đa 500 ký tự) để vừa vặn khung ảnh Telegram.

PHẦN 1 (Bối cảnh vĩ mô & Kịch bản VN-Index hôm nay):
🌐 **Bối cảnh Vĩ mô & Quốc tế:**
• [Tóm tắt ngắn gọn tình hình chứng khoán Mỹ, DXY/Tỷ giá, Giá dầu/vàng và tâm lý liên thị trường]
📊 **Tổng quan Kỹ thuật VN-Index:**
• Điểm số kết phiên: {ta.get('last_close'):,.2f} ({'+' if ta.get('change_price', 0) >= 0 else ''}{ta.get('change_price'):.2f} điểm)
• MA20: {ta.get('sma20'):,.2f} | RSI: {ta.get('rsi'):.1f} | Thanh khoản: {ta.get('vol_ratio'):.1f}x TB20
• [Đánh giá ngắn gọn trạng thái cung cầu và xu hướng chính]
🎯 **Kịch bản VN-Index phiên hôm nay:**
• **Vùng kháng cự:** [Nêu vùng điểm cụ thể]
• **Vùng hỗ trợ:** [Nêu vùng điểm cụ thể]
• **Xu hướng dự kiến:** [Mô tả kịch bản dao động khả dĩ nhất]

===SPLIT===

PHẦN 2 (Nhóm ngành ưu tiên vĩ mô & Chiến lược giải ngân đầu phiên):
⭐ **DANH MỤC NHÓM NGÀNH ƯU TIÊN VĨ MÔ (TIỀM NĂNG TĂNG TRƯỞNG CAO NHẤT):**
• 🥇 **[Tên ngành ưu tiên 1]:** [Động lực vĩ mô then chốt] ➔ Cổ phiếu trọng tâm: #[Mã1], #[Mã2]
• 🥈 **[Tên ngành ưu tiên 2]:** [Động lực vĩ mô then chốt] ➔ Cổ phiếu trọng tâm: #[Mã1], #[Mã2]
• 🥉 **[Tên ngành ưu tiên 3]:** [Động lực vĩ mô then chốt] ➔ Cổ phiếu trọng tâm: #[Mã1], #[Mã2]

🏢 **GÓC NHÌN CÁC NHÓM NGÀNH KHÁC:**
• 🏦 **Ngân hàng:** [Nhận định dòng tiền]
• 📈 **Chứng khoán:** [Nhận định dòng tiền]
• 🏗️ **Bất động sản:** [Nhận định dòng tiền]

🎯 **Chiến lược hành động & Phân bổ vốn quỹ đầu ngày:**
• **Tỷ trọng cổ phiếu khuyến nghị:** [Ví dụ: 60-70% / 50% ...]
• **Kỷ luật mở phiên:** [Khuyến nghị cụ thể: Tránh mua đuổi ATO, canh nhịp rung lắc để gom các nhóm ngành ưu tiên vĩ mô]
"""
    raw_text = ai_analyzer.call_gemini(prompt)
    if not raw_text:
        return None

    if "===SPLIT===" in raw_text:
        parts = raw_text.split("===SPLIT===")
        part1 = parts[0].strip()
        part2 = parts[1].strip()
    elif "⭐ **DANH MỤC" in raw_text:
        parts = raw_text.split("⭐ **DANH MỤC")
        part1 = parts[0].strip()
        part2 = "⭐ **DANH MỤC" + parts[1]
    elif "🏢 **GÓC NHÌN" in raw_text:
        parts = raw_text.split("🏢 **GÓC NHÌN")
        part1 = parts[0].strip()
        part2 = "🏢 **GÓC NHÌN" + parts[1]
    else:
        part1 = raw_text[:800].strip()
        part2 = raw_text[800:].strip()

    # Tái cân bằng nếu part1 quá ngắn do AI chèn lời chào trước SPLIT
    if len(part1) < 180 and len(part2) > 200:
        combined = part1 + "\n\n" + part2
        if "⭐ **DANH MỤC" in combined:
            s = combined.split("⭐ **DANH MỤC")
            part1 = s[0].strip()
            part2 = "⭐ **DANH MỤC" + s[1]
        elif "🏢 **GÓC NHÌN" in combined:
            s = combined.split("🏢 **GÓC NHÌN")
            part1 = s[0].strip()
            part2 = "🏢 **GÓC NHÌN" + s[1]

    return chart_buf, part1, part2

async def broadcast_morning_macro(bot: Bot, force: bool = False) -> bool:
    """
    Phát sóng bản tin vĩ mô đầu ngày lên Kênh Telegram lúc 8h sáng:
    - Kiểm tra ngày giao dịch (trừ Thứ 7, Chủ Nhật và ngày lễ).
    - Đoạn 1: Ảnh nến kỹ thuật VN-Index + Bối cảnh vĩ mô & Kịch bản phiên.
    - Đoạn 2: Reply đoạn 1 với Điểm tin nhóm ngành & Chiến lược giải ngân.
    """
    now = datetime.now(VIETNAM_TZ)
    today_str = now.strftime("%Y-%m-%d")

    # Nếu không phải lệnh cưỡng chế chạy thử, kiểm tra lịch giao dịch và tránh gửi lặp
    if not force:
        if not holiday_checker.is_vietnam_trading_day(now):
            logger.info(f"Hôm nay ({today_str}) là ngày nghỉ sàn chứng khoán (Cuối tuần/Ngày lễ). Bỏ qua bản tin 8h sáng.")
            return False

        if db.is_macro_sent_today(today_str):
            logger.info(f"Bản tin vĩ mô ngày {today_str} đã được gửi trước đó. Bỏ qua.")
            return False

    logger.info(f"Bắt đầu khởi tạo bản tin vĩ mô đầu ngày cho ngày {today_str}...")
    report = generate_morning_macro_content()
    if not report:
        logger.error("Không tạo được nội dung bản tin vĩ mô.")
        return False

    chart_buf, part1, part2 = report

    # Trích xuất và cập nhật các nhóm ngành ưu tiên vĩ mô vào Database làm định hướng đầu tư
    priority_sectors = ai_analyzer.extract_macro_priority_sectors(part1 + "\n" + part2)
    if priority_sectors:
        db.set_macro_priority_sectors(priority_sectors, today_str)
        logger.info(f"Đã cập nhật {len(priority_sectors)} nhóm ngành ưu tiên vĩ mô vào Database.")

    weekday_name = WEEKDAYS_VN.get(now.weekday(), "Thứ Hai")
    date_display = f"{weekday_name}, ngày {now.strftime('%d/%m/%Y')}"

    # 1. ĐOẠN GỐC: Ảnh biểu đồ nến VNINDEX kèm Vĩ mô & Kịch bản phiên
    caption_root = (
        "🌅 **BẢN TIN VĨ MÔ ĐẦU NGÀY | MACET FINANCE**\n"
        f"📅 *{date_display}*\n\n"
        f"{part1}"
    )

    if len(caption_root) > 1000:
        caption_root = caption_root[:995] + "..."

    clean_plain_caption = caption_root.replace("**", "").replace("`", "")

    try:
        photo = BufferedInputFile(chart_buf.getvalue(), filename="vnindex_morning.png")
        try:
            root_msg = await bot.send_photo(
                chat_id=config.TELEGRAM_CHANNEL_ID,
                photo=photo,
                caption=caption_root,
                parse_mode=ParseMode.MARKDOWN
            )
        except TelegramBadRequest as e_cap:
            logger.warning(f"Lỗi markdown caption macro ({e_cap}), gửi bằng plain text...")
            root_msg = await bot.send_photo(
                chat_id=config.TELEGRAM_CHANNEL_ID,
                photo=BufferedInputFile(chart_buf.getvalue(), filename="vnindex_morning.png"),
                caption=clean_plain_caption,
                parse_mode=None
            )
        orig_id = root_msg.message_id
        logger.info(f"Đã đăng bản tin vĩ mô gốc ID {orig_id} lên kênh")

        # 2. ĐOẠN THỨ 2: Reply đoạn gốc với Điểm tin nhóm ngành & Chiến lược giải ngân
        if part2:
            await asyncio.sleep(2)
            msg_part2 = (
                f"{part2}\n\n"
                "──────────────────\n"
                f"📢 **Macet Finance Research** | Chúc quý nhà đầu tư phiên giao dịch hiệu quả!"
            )
            # Chia nhỏ nếu vượt quá giới hạn 4000 ký tự của Telegram
            chunks = []
            while len(msg_part2) > 4000:
                split_idx = msg_part2[:4000].rfind("\n")
                if split_idx == -1:
                    split_idx = 4000
                chunks.append(msg_part2[:split_idx])
                msg_part2 = msg_part2[split_idx:].strip()
            if msg_part2:
                chunks.append(msg_part2)

            for chunk in chunks:
                clean_chunk = chunk.replace("**", "").replace("`", "")
                try:
                    await bot.send_message(
                        chat_id=config.TELEGRAM_CHANNEL_ID,
                        text=chunk,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_parameters=ReplyParameters(message_id=orig_id)
                    )
                except TelegramBadRequest as e_p2:
                    logger.warning(f"Lỗi markdown part2 macro ({e_p2}), gửi bằng plain text...")
                    await bot.send_message(
                        chat_id=config.TELEGRAM_CHANNEL_ID,
                        text=clean_chunk,
                        parse_mode=None,
                        reply_parameters=ReplyParameters(message_id=orig_id)
                    )
                await asyncio.sleep(1)
            logger.info(f"Đã gửi đoạn 2 (Nhóm ngành & Chiến lược) reply tin gốc {orig_id}")

        # Ghi nhận đã gửi bản tin cho ngày hôm nay
        db.mark_macro_sent_today(today_str)
        return True

    except Exception as e:
        logger.error(f"Lỗi khi gửi bản tin vĩ mô lên kênh: {e}")
        return False
