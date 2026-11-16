import os
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

import config
import db
import holiday_checker
import data_fetcher
import technical_analysis
import chart_generator
import ai_analyzer
import news_broadcaster
import macro_broadcaster
import portfolio_manager
import portfolio_monitor
import table_image_generator
import closing_portfolio_broadcaster
import pending_order_executor

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
VIETNAM_TZ = ZoneInfo("Asia/Bangkok")

def get_stock_action_keyboard(symbol: str) -> InlineKeyboardMarkup:
    """Tạo menu nút bấm tương tác cho mã cổ phiếu"""
    kb = [
        [
            InlineKeyboardButton(text="📊 Biểu Đồ & PTKT", callback_data=f"ta_{symbol}"),
            InlineKeyboardButton(text="📰 Tin Tức", callback_data=f"news_{symbol}")
        ],
        [
            InlineKeyboardButton(text="📢 Bắn Báo Cáo Lên Kênh", callback_data=f"broadcast_{symbol}"),
            InlineKeyboardButton(text="🔄 Cập Nhật Giá", callback_data=f"price_{symbol}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """Lệnh /start"""
    text = (
        "👋 **Chào mừng bạn đến với Macet Finance Research!**\n\n"
        f"Hệ thống phân tích chiến lược & Quản trị Danh mục Quỹ 1 Tỷ đồng, đồng bộ trực tiếp với Kênh {config.TELEGRAM_CHANNEL_USERNAME}.\n\n"
        "📌 **Các tính năng chính:**\n"
        "• `/danhmuc` - Xem Ảnh Bảng Biểu Danh Mục Đầu Tư Quỹ 1 Tỷ\n"
        "• `/post_danhmuc` - Phát sóng Bảng danh mục dạng ảnh lên Kênh\n"
        "• `/post_macro` - Phát sóng Bản tin Vĩ mô đầu ngày (8h00 sáng)\n"
        "• `/post_ta <mã>` - Đăng báo cáo phân tích cổ phiếu kèm biểu đồ lên Kênh Telegram\n"
        "• `/post_tin` - Quét tin tức mới nhất, AI ra quyết định đầu tư và đăng lên Kênh\n"
        "• `/gia <mã>` - Tra cứu biến động giá & thanh khoản phiên (VD: `/gia HPG`)\n"
        "• `/ta <mã>` - Biểu đồ nến kỹ thuật & Nhận định chiến lược từ Macet Finance\n"
        "• `/tin` - Đọc tin tức thị trường mới nhất\n"
        "• `/help` - Xem hướng dẫn sử dụng chi tiết\n\n"
        "💡 *Mẹo:* Bạn có thể gõ trực tiếp mã 3 ký tự (VD: `HPG`, `FPT`, `SSI`) vào chat!"
    )
    quick_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Bảng Danh Mục Dạng Ảnh", callback_data="view_portfolio"),
            InlineKeyboardButton(text="📢 Đăng Bảng Lên Kênh", callback_data="trigger_post_danhmuc")
        ],
        [
            InlineKeyboardButton(text="🌅 Bắn Bản Tin Vĩ Mô", callback_data="trigger_post_macro"),
            InlineKeyboardButton(text="📰 Xem Tin Tức Nóng", callback_data="global_news")
        ]
    ])
    await message.answer(text, reply_markup=quick_kb, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("danhmuc"))
@dp.message(Command("portfolio"))
async def cmd_danhmuc(message: types.Message):
    """Lệnh /danhmuc - Xuất ảnh bảng biểu danh mục đầu tư quỹ 1 tỷ"""
    await send_portfolio_report(message)

async def send_portfolio_report(target):
    now = datetime.now(VIETNAM_TZ)
    weekday_name = macro_broadcaster.WEEKDAYS_VN.get(now.weekday(), "Thứ Hai")
    date_display = f"{weekday_name}, ngày {now.strftime('%d/%m/%Y')}"

    summary = portfolio_manager.get_portfolio_summary()
    img_buf = table_image_generator.render_portfolio_table_image(summary, date_display)

    initial_cap = summary["initial_capital"]
    total_assets = summary["total_assets"]
    cash = summary["cash_balance"]
    stock_val = summary["stock_value"]
    pnl_total = summary["pnl_total"]
    pnl_pct = summary["pnl_total_pct"]

    icon_pnl = "🟢" if pnl_total >= 0 else "🔴"
    sign_pnl = "+" if pnl_total >= 0 else ""

    caption = (
        "💼 **BÁO CÁO DANH MỤC ĐẦU TƯ QUỸ MACET FINANCE**\n\n"
        f"💵 **Vốn ban đầu:** `{initial_cap:,.0f} VNĐ`\n"
        f"💰 **Tổng tài sản hiện tại:** `{total_assets:,.0f} VNĐ`\n"
        f"{icon_pnl} **Lợi nhuận ròng:** `{sign_pnl}{pnl_total:,.0f} VNĐ` (`{sign_pnl}{pnl_pct:.2f}%`)\n"
        f"💵 **Tiền mặt:** `{cash:,.0f} VNĐ` ({(cash/total_assets)*100:.1f}%) | "
        f"📦 **Cổ phiếu:** `{stock_val:,.0f} VNĐ` ({(stock_val/total_assets)*100:.1f}%)\n\n"
        "📌 *Chi tiết từng mã, số lượng, tỷ trọng % tài sản, lãi/lỗ và ngưỡng TP/SL được chia hàng chia cột rõ nét trong ảnh bảng biểu phía trên.*"
    )

    photo = BufferedInputFile(img_buf.getvalue(), filename="portfolio_table.png")
    if isinstance(target, types.CallbackQuery):
        await target.message.answer_photo(photo=photo, caption=caption, parse_mode=ParseMode.MARKDOWN)
    else:
        await target.answer_photo(photo=photo, caption=caption, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("post_danhmuc"))
async def cmd_post_danhmuc(message: types.Message):
    """Lệnh cưỡng chế phát sóng Bảng danh mục cuối phiên lên Kênh"""
    msg = await message.answer("⏳ Đang tổng hợp và phát sóng Ảnh Bảng biểu Danh mục lên Kênh...")
    ok = await closing_portfolio_broadcaster.broadcast_closing_portfolio(bot, force=True)
    if ok:
        await msg.edit_text(f"✅ Đã phát sóng thành công Ảnh Bảng biểu Danh mục lên Kênh {config.TELEGRAM_CHANNEL_USERNAME}!")
    else:
        await msg.edit_text("❌ Không thể phát sóng bảng danh mục.")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Lệnh /help"""
    text = (
        "📖 **HƯỚNG DẪN SỬ DỤNG MACET FINANCE BOT**\n\n"
        "1️⃣ **Quản lý danh mục quỹ 1 tỷ:**\n"
        "  • `/danhmuc`: Xuất Ảnh Bảng Biểu chia hàng chia cột chi tiết tài sản, lãi/lỗ và danh mục.\n"
        "  • `/post_danhmuc`: Đăng Ảnh Bảng biểu danh mục cuối phiên lên Kênh.\n\n"
        "2️⃣ **Tra cứu giá & Phân tích kỹ thuật:**\n"
        "  • `/gia <mã>` (Ví dụ: `/gia VNM`) hoặc gõ thẳng mã `VNM`.\n"
        "  • `/ta <mã>` (Ví dụ: `/ta HPG`): Vẽ nến kèm MA20/50, RSI, MACD và góc nhìn chiến lược.\n\n"
        "3️⃣ **Quản trị Kênh Telegram:**\n"
        "  • `/post_macro`: Phát sóng Bản tin Vĩ mô đầu ngày (8h00 sáng).\n"
        f"  • `/post_ta <mã>`: Bắn báo cáo phân tích theo chuỗi lên kênh {config.TELEGRAM_CHANNEL_USERNAME}.\n"
        "  • `/post_tin`: Quét tin nóng mới nhất, tự động ra quyết định đầu tư (Mua mới/Mua thêm/Bán bớt) và đăng lên kênh.\n\n"
        "4️⃣ **Lịch tự động hóa (Trừ Thứ 7, Chủ Nhật và ngày lễ):**\n"
        "  • **08:00 Sáng:** Tự động phát sóng Bản tin Vĩ mô đầu ngày.\n"
        "  • **15:30 Chiều:** Tự động phát sóng Ảnh Bảng biểu Tổng kết Danh mục cuối phiên.\n"
        f"  • **Mỗi {config.AUTO_NEWS_INTERVAL_SECONDS}s:** Quét tin tức mới, ra quyết định đầu tư và giám sát chốt lời/cắt lỗ cho danh mục."
    )
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("post_macro"))
async def cmd_post_macro(message: types.Message):
    """Lệnh cưỡng chế phát Bản tin Vĩ mô đầu ngày lên kênh"""
    msg = await message.answer("⏳ Đang tổng hợp dữ liệu VN-Index và khởi tạo Bản tin Vĩ mô đầu ngày...")
    ok = await macro_broadcaster.broadcast_morning_macro(bot, force=True)
    if ok:
        await msg.edit_text(f"✅ Đã phát sóng thành công Bản tin Vĩ mô đầu ngày lên Kênh {config.TELEGRAM_CHANNEL_USERNAME}!")
    else:
        await msg.edit_text("❌ Không thể tạo hoặc phát sóng bản tin vĩ mô.")

@dp.message(Command("tin"))
async def cmd_news(message: types.Message):
    """Lệnh /tin"""
    news_items = data_fetcher.get_latest_news(limit=5)
    if not news_items:
        await message.answer("⚠️ Hiện không thể tải tin tức, vui lòng thử lại sau.")
        return

    text = "📰 **TIN TỨC CHỨNG KHOÁN MỚI NHẤT (CafeF):**\n\n"
    for i, item in enumerate(news_items, 1):
        text += f"{i}. [{item['title']}]({item['link']})\n\n"

    await message.answer(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

@dp.message(Command("post_tin"))
async def cmd_post_tin(message: types.Message):
    """Lệnh cưỡng chế quét tin tức và đăng lên kênh kèm quyết định đầu tư"""
    msg = await message.answer("⏳ Đang quét tin tức mới và đánh giá quyết định đầu tư...")
    count = await news_broadcaster.check_and_broadcast_news(bot, max_posts=1)
    if count > 0:
        await msg.edit_text(f"✅ Đã phân tích và đăng thành công {count} bản tin lên Kênh {config.TELEGRAM_CHANNEL_USERNAME} (kèm quyết định đầu tư & cập nhật tài sản)!")
    else:
        await msg.edit_text(f"ℹ️ Không có tin tức mới nào chưa đăng trên Kênh {config.TELEGRAM_CHANNEL_USERNAME}.")

@dp.message(Command("post_ta"))
async def cmd_post_ta(message: types.Message):
    """Lệnh /post_ta <mã> - Đăng phân tích cổ phiếu lên kênh theo chuỗi reply"""
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("⚠️ Vui lòng nhập mã cổ phiếu. Ví dụ: `/post_ta HPG`", parse_mode=ParseMode.MARKDOWN)
        return
    
    symbol = parts[1].strip().upper()
    msg = await message.answer(f"⏳ Đang vẽ biểu đồ và khởi tạo báo cáo cho `#{symbol}`...")
    ok = await news_broadcaster.broadcast_stock_analysis(bot, symbol)
    if ok:
        await msg.edit_text(f"✅ Đã đăng thành công báo cáo #{symbol} lên Kênh {config.TELEGRAM_CHANNEL_USERNAME} (chuỗi 3 tin nhắn liên kết)!")
    else:
        await msg.edit_text(f"❌ Có lỗi khi đăng báo cáo #{symbol} lên Kênh.")

@dp.message(Command("gia"))
async def cmd_price(message: types.Message):
    """Lệnh /gia <mã>"""
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("⚠️ Vui lòng nhập mã cổ phiếu. Ví dụ: `/gia HPG`", parse_mode=ParseMode.MARKDOWN)
        return
    
    symbol = parts[1].strip().upper()
    await send_price_info(message, symbol)

@dp.message(Command("ta"))
async def cmd_ta(message: types.Message):
    """Lệnh /ta <mã>"""
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("⚠️ Vui lòng nhập mã cổ phiếu. Ví dụ: `/ta HPG`", parse_mode=ParseMode.MARKDOWN)
        return
    
    symbol = parts[1].strip().upper()
    await send_ta_analysis(message, symbol)

async def send_price_info(target, symbol: str):
    """Gửi thông tin giá nhanh"""
    df = data_fetcher.get_stock_history(symbol, days=30)
    info = data_fetcher.get_symbol_info(symbol)

    if df is None or len(df) < 2:
        msg = f"❌ Không tìm thấy dữ liệu cho mã `{symbol}`. Vui lòng kiểm tra lại mã cổ phiếu!"
        if isinstance(target, types.CallbackQuery):
            await target.message.answer(msg, parse_mode=ParseMode.MARKDOWN)
        else:
            await target.answer(msg, parse_mode=ParseMode.MARKDOWN)
        return

    last_close = df["Close"].iloc[-1]
    prev_close = df["Close"].iloc[-2]
    high = df["High"].iloc[-1]
    low = df["Low"].iloc[-1]
    vol = df["Volume"].iloc[-1]
    change = last_close - prev_close
    pct_change = (change / prev_close) * 100

    icon = "🟢" if change > 0 else ("🔴" if change < 0 else "🟡")
    sign = "+" if change > 0 else ""
    desc = info.get("description", "") if info else ""
    exchange = info.get("exchange-traded", "") if info else ""

    text = (
        f"📊 **MÃ CỔ PHIẾU: #{symbol}** ({exchange})\n"
        f"_{desc}_\n\n"
        f"💵 **Giá hiện tại:** `{last_close:,.2f}` nghìn VNĐ\n"
        f"{icon} **Biến động:** `{sign}{change:,.2f}` (`{sign}{pct_change:.2f}%`)\n"
        f"📈 **Cao nhất phiên:** `{high:,.2f}`\n"
        f"📉 **Thấp nhất phiên:** `{low:,.2f}`\n"
        f"📦 **Khối lượng:** `{vol:,.0f}` cp\n\n"
        f"⏱ _Cập nhật theo dữ liệu phiên gần nhất_"
    )
    kb = get_stock_action_keyboard(symbol)
    if isinstance(target, types.CallbackQuery):
        await target.message.answer(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    else:
        await target.answer(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

async def send_ta_analysis(target, symbol: str):
    """Gửi biểu đồ nến kèm phân tích kỹ thuật và góc nhìn chiến lược"""
    loading_msg = None
    if isinstance(target, types.CallbackQuery):
        loading_msg = await target.message.answer(f"⏳ Đang tải dữ liệu và phân tích `{symbol}`...")
    else:
        loading_msg = await target.answer(f"⏳ Đang tải dữ liệu và phân tích `{symbol}`...")

    df = data_fetcher.get_stock_history(symbol, days=180)
    if df is None or len(df) < 30:
        await loading_msg.edit_text(f"❌ Không đủ dữ liệu kỹ thuật để phân tích mã `{symbol}`.", parse_mode=ParseMode.MARKDOWN)
        return

    analysis = technical_analysis.analyze_stock(df)
    chart_buf = chart_generator.generate_candlestick_chart(df, symbol)
    stock_analysis = ai_analyzer.analyze_stock_with_ai(symbol, analysis)

    if not analysis or not chart_buf:
        await loading_msg.edit_text(f"❌ Lỗi khi phân tích biểu đồ `{symbol}`.", parse_mode=ParseMode.MARKDOWN)
        return

    signals_text = "\n".join([f"• {s}" for s in analysis["signals"]])
    caption = (
        f"📈 **PHÂN TÍCH KỸ THUẬT: #{symbol}**\n\n"
        f"🎯 **Đánh giá xu hướng:** {analysis['summary']}\n\n"
        f"📊 **Chỉ số kỹ thuật:**\n"
        f"• Giá: `{analysis['last_close']:,.2f}` ({'+' if analysis['change_price'] >= 0 else ''}{analysis['pct_change']:.2f}%)\n"
        f"• MA20: `{analysis['sma20']:,.2f}` | MA50: `{analysis['sma50']:,.2f}`\n"
        f"• RSI(14): `{analysis['rsi']:.1f}`\n"
        f"• Khối lượng: `{analysis['vol_ratio']:.1f}x` TB20 phiên\n\n"
        f"🔍 **Tín hiệu kỹ thuật:**\n{signals_text}\n"
    )

    photo = BufferedInputFile(chart_buf.getvalue(), filename=f"{symbol}_ta.png")
    kb = get_stock_action_keyboard(symbol)

    if isinstance(target, types.CallbackQuery):
        await target.message.answer_photo(photo=photo, caption=caption, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        if stock_analysis:
            part1, part2 = stock_analysis
            full_commentary = f"{part1}\n\n{part2}" if part2 else part1
            await target.message.answer(f"{full_commentary}", parse_mode=ParseMode.MARKDOWN)
    else:
        await target.answer_photo(photo=photo, caption=caption, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        if stock_analysis:
            part1, part2 = stock_analysis
            full_commentary = f"{part1}\n\n{part2}" if part2 else part1
            await target.answer(f"{full_commentary}", parse_mode=ParseMode.MARKDOWN)

    try:
        await loading_msg.delete()
    except Exception:
        pass

# Callbacks
@dp.callback_query(F.data == "view_portfolio")
async def callback_view_portfolio(query: types.CallbackQuery):
    await query.answer()
    await send_portfolio_report(query)

@dp.callback_query(F.data == "trigger_post_danhmuc")
async def callback_trigger_post_danhmuc(query: types.CallbackQuery):
    await query.answer("Đang phát sóng bảng danh mục dạng ảnh...")
    ok = await closing_portfolio_broadcaster.broadcast_closing_portfolio(bot, force=True)
    if ok:
        await query.message.answer(f"✅ Đã phát sóng Bảng danh mục dạng ảnh lên Kênh {config.TELEGRAM_CHANNEL_USERNAME}!")
    else:
        await query.message.answer("❌ Không thể phát sóng bảng danh mục.")

@dp.callback_query(F.data == "trigger_post_macro")
async def callback_trigger_post_macro(query: types.CallbackQuery):
    await query.answer("Đang tạo Bản tin Vĩ mô đầu ngày...")
    ok = await macro_broadcaster.broadcast_morning_macro(bot, force=True)
    if ok:
        await query.message.answer(f"✅ Đã phát sóng Bản tin Vĩ mô đầu ngày lên Kênh {config.TELEGRAM_CHANNEL_USERNAME}!")
    else:
        await query.message.answer("❌ Không thể tạo Bản tin Vĩ mô.")

@dp.callback_query(F.data.startswith("price_"))
async def callback_price(query: types.CallbackQuery):
    symbol = query.data.split("_")[1]
    await query.answer()
    await send_price_info(query, symbol)

@dp.callback_query(F.data.startswith("ta_"))
async def callback_ta(query: types.CallbackQuery):
    symbol = query.data.split("_")[1]
    await query.answer()
    await send_ta_analysis(query, symbol)

@dp.callback_query(F.data.startswith("broadcast_"))
async def callback_broadcast(query: types.CallbackQuery):
    symbol = query.data.split("_")[1]
    await query.answer("Đang xuất bản báo cáo lên kênh...")
    ok = await news_broadcaster.broadcast_stock_analysis(bot, symbol)
    if ok:
        await query.message.answer(f"✅ Đã gửi báo cáo #{symbol} lên Kênh {config.TELEGRAM_CHANNEL_USERNAME}!")
    else:
        await query.message.answer(f"❌ Không thể gửi báo cáo #{symbol} lên Kênh.")

@dp.callback_query(F.data.startswith("news_"))
async def callback_news(query: types.CallbackQuery):
    symbol = query.data.split("_")[1]
    await query.answer()
    news = data_fetcher.get_stock_news(symbol, limit=3)
    if not news:
        news = data_fetcher.get_latest_news(limit=3)
        header = f"📰 Tin tức liên quan đến `{symbol}` chưa có, sau đây là tin thị trường mới nhất:"
    else:
        header = f"📰 Tin tức mới nhất liên quan đến **{symbol}**:"

    text = f"{header}\n\n"
    for i, item in enumerate(news, 1):
        text += f"{i}. [{item['title']}]({item['link']})\n\n"
    
    kb = get_stock_action_keyboard(symbol)
    await query.message.answer(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

@dp.callback_query(F.data == "trigger_post_news")
async def callback_trigger_post_news(query: types.CallbackQuery):
    await query.answer("Đang quét tin mới...")
    count = await news_broadcaster.check_and_broadcast_news(bot, max_posts=1)
    if count > 0:
        await query.message.answer(f"✅ Đã đăng {count} bản tin mới lên Kênh {config.TELEGRAM_CHANNEL_USERNAME}!")
    else:
        await query.message.answer(f"ℹ️ Không có tin tức mới nào chưa đăng trên Kênh.")

@dp.callback_query(F.data == "global_news")
async def callback_global_news(query: types.CallbackQuery):
    await query.answer()
    news_items = data_fetcher.get_latest_news(limit=5)
    text = "📰 **TIN TỨC CHỨNG KHOÁN MỚI NHẤT (CafeF):**\n\n"
    for i, item in enumerate(news_items, 1):
        text += f"{i}. [{item['title']}]({item['link']})\n\n"
    await query.message.answer(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

# Direct Text Input (e.g. HPG, FPT)
@dp.message(F.text)
async def handle_direct_text(message: types.Message):
    text = message.text.strip().upper()
    if len(text) == 3 and text.isalpha():
        await send_price_info(message, text)
    elif text in ["VNINDEX", "VN30", "HNX"]:
        await send_price_info(message, text)
    else:
        await message.answer(
            f"💡 Bạn vừa nhập `{text}`. Hãy nhập mã 3 ký tự (VD: `HPG`, `FPT`) hoặc dùng lệnh `/gia {text}`, `/ta {text}`, `/danhmuc`.",
            parse_mode=ParseMode.MARKDOWN
        )

# Vòng lặp định kỳ (Bản tin 8h sáng, Tổng kết 15h30 dạng ảnh, Quét tin & Giám sát chốt lời/cắt lỗ)
async def automated_scheduler_loop(bot_instance: Bot):
    logger.info("Tiến trình lập lịch tự động (Bản tin 8h sáng, Tổng kết 15h30 dạng ảnh & Quản trị danh mục) đã khởi động...")
    await asyncio.sleep(5)
    while True:
        try:
            now = datetime.now(VIETNAM_TZ)
            today_str = now.strftime("%Y-%m-%d")
            is_trading = holiday_checker.is_vietnam_trading_day(now)

            # 1. Bản tin Vĩ mô đầu ngày (8h00 sáng, Thứ 2 - Thứ 6, trừ ngày lễ)
            if now.hour == 8 and now.minute == 0 and is_trading:
                if not db.is_macro_sent_today(today_str):
                    logger.info(f"Đến 8h00 sáng ngày {today_str}. Kích hoạt Bản tin Vĩ mô đầu ngày...")
                    await macro_broadcaster.broadcast_morning_macro(bot_instance, force=False)

            # 2. Bảng tổng kết danh mục đầu tư cuối phiên dạng ẢNH (15h30 chiều, Thứ 2 - Thứ 6, trừ ngày lễ)
            if now.hour == 15 and now.minute == 30 and is_trading:
                if not portfolio_manager.is_closing_report_sent_today(today_str):
                    logger.info(f"Đến 15h30 chiều ngày {today_str}. Kích hoạt Bảng danh mục dạng ẢNH...")
                    await closing_portfolio_broadcaster.broadcast_closing_portfolio(bot_instance, force=False)

            # 3. Khớp lệnh cho các vị thế đã lên kế hoạch ngoài giờ khi sàn vào phiên chính thức
            await pending_order_executor.execute_pending_orders(bot_instance)

            # 4. Giám sát các mã đang nắm giữ: Tự động chốt lời / cắt lỗ kỷ luật
            await portfolio_monitor.check_portfolio_triggers(bot_instance)

            # 5. Quét tin tức thời gian thực & Ra quyết định đầu tư
            await news_broadcaster.check_and_broadcast_news(bot_instance, max_posts=1)

        except Exception as e:
            logger.error(f"[Scheduler Loop] Lỗi: {e}")

        # Kiểm tra định kỳ mỗi 30 giây
        await asyncio.sleep(30)

# HTTP Server siêu nhẹ phục vụ Health Check cho các nền tảng Cloud (Render, Koyeb, v.v.)
async def start_health_server():
    port = int(os.getenv("PORT", "8080"))
    
    async def handle_http(reader, writer):
        try:
            line = await reader.readline()
            while True:
                header = await reader.readline()
                if not header or header == b"\r\n":
                    break
            body = b'{"status": "ok", "app": "Macet Finance Research Bot", "version": "2.0"}\n'
            response = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: application/json\r\n"
                f"Content-Length: {len(body)}\r\n"
                b"Connection: close\r\n\r\n"
            ) + body
            writer.write(response)
            await writer.drain()
        except Exception:
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    try:
        server = await asyncio.start_server(handle_http, "0.0.0.0", port)
        logger.info(f"Health check HTTP Server đang chạy trên cổng {port} (Sẵn sàng cho Cloud Web Service)...")
        return server
    except Exception as e:
        logger.warning(f"Không thể khởi tạo HTTP Server trên cổng {port}: {e}")
        return None

async def main():
    logger.info(f"Macet Finance Bot đang khởi động với Kênh {config.TELEGRAM_CHANNEL_USERNAME}...")
    db.init_db()
    portfolio_manager.init_portfolio_db()
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Khởi chạy HTTP Health Check Server cho Cloud
    asyncio.create_task(start_health_server())

    # Khởi chạy vòng lặp lập lịch tự động
    asyncio.create_task(automated_scheduler_loop(bot))
    
    # Bắt đầu nhận tin nhắn
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot đã dừng.")
