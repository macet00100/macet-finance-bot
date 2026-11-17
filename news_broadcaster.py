import asyncio
import logging
import time
import feedparser
import httpx
from bs4 import BeautifulSoup
from typing import Optional, Tuple, List
from aiogram import Bot
from aiogram.types import BufferedInputFile, ReplyParameters
from aiogram.enums import ParseMode

import config
import db
import ai_analyzer
import data_fetcher
import technical_analysis
import chart_generator
import portfolio_manager
import investment_engine

logger = logging.getLogger(__name__)

# Khóa chống xung đột và cache trong bộ nhớ để triệt tiêu mọi khả năng lặp tin
_broadcast_lock = asyncio.Lock()
_processing_titles = set()

RSS_FEEDS = [
    "https://cafef.vn/thi-truong-chung-khoan.rss",
    "https://cafef.vn/doanh-nghiep.rss",
    "https://cafef.vn/tai-chinh-ngan-hang.rss"
]

def extract_image_and_summary(entry) -> Tuple[Optional[str], str]:
    """Trích xuất link ảnh thumbnail và nội dung tóm tắt từ RSS entry"""
    summary_html = entry.get("summary", "")
    soup = BeautifulSoup(summary_html, "html.parser")
    
    img_tag = soup.find("img")
    img_url = img_tag["src"] if (img_tag and "src" in img_tag.attrs) else None
    
    clean_summary = soup.get_text().strip()
    if not clean_summary:
        clean_summary = entry.get("title", "")
    return img_url, clean_summary

async def download_image_bytes(url: str) -> Optional[bytes]:
    """Tải nội dung ảnh từ URL về dạng byte buffer"""
    if not url:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.content
    except Exception as e:
        logger.warning(f"Không thể tải ảnh từ {url}: {e}")
    return None

def seed_existing_news():
    """Đánh dấu tất cả tin tức hiện có trên RSS feeds là đã đọc khi bot khởi động lần đầu để chống đăng dồn dập tin cũ"""
    total = 0
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                news_id = entry.link
                title = entry.title.strip()
                if not db.is_news_published(news_id, title):
                    db.mark_news_published(news_id, title)
                    total += 1
        except Exception as e:
            logger.warning(f"Lỗi khi seed tin tức từ {feed_url}: {e}")
    if total > 0:
        logger.info(f"Đã seed {total} tin tức cũ vào cơ sở dữ liệu để chống đăng trùng lặp khi khởi động.")

async def check_and_broadcast_news(bot: Bot, max_posts: int = 1) -> int:
    """
    Quét tin tức mới:
    - Sử dụng _broadcast_lock chống chạy chồng chéo / chạy song song.
    - Chuẩn hóa tiêu đề bài viết và kiểm tra chống trùng lặp đa tầng.
    - Đánh dấu đã đăng NGAY LẬP TỨC khi tin gốc được gửi thành công lên Kênh Telegram.
    - Đảm bảo Đoạn 2 (nhận định chuyên sâu) tuyệt đối không bị đứt đoạn hay ngắn cụt.
    """
    if _broadcast_lock.locked():
        logger.info("Tiến trình quét tin khác đang xử lý, tạm bỏ qua lượt này để chống trùng lặp.")
        return 0

    async with _broadcast_lock:
        posted_count = 0
        seen_in_batch = set()
        
        for feed_url in RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries:
                    news_id = entry.link
                    title = entry.title.strip()
                    norm_title = db.normalize_title(title)
                    img_url, clean_summary = extract_image_and_summary(entry)

                    # Chống lặp trong cùng đợt quét & in-memory cache
                    if norm_title in seen_in_batch or norm_title in _processing_titles or news_id in seen_in_batch:
                        continue
                    seen_in_batch.add(norm_title)
                    seen_in_batch.add(news_id)

                    # Kiểm tra cơ sở dữ liệu theo cả URL và Tiêu đề chuẩn hóa
                    if db.is_news_published(news_id, title):
                        continue

                    # Lọc độ tươi mới: chỉ lấy tin trong vòng 2 tiếng gần nhất
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        try:
                            entry_ts = time.mktime(entry.published_parsed)
                            if (time.time() - entry_ts) > 7200:
                                db.mark_news_published(news_id, title)
                                continue
                        except Exception:
                            pass

                    # Khóa tạm thời tiêu đề này trong bộ nhớ để chặn hoàn toàn mọi luồng khác
                    _processing_titles.add(norm_title)

                    logger.info(f"Phát hiện tin mới: {title}")
                    
                    # 1. Phân tích tin tức & Phân loại phạm vi (MULTI_SECTOR vs SPECIFIC)
                    mapping = ai_analyzer.analyze_news_mapping(title, clean_summary)
                    if not mapping:
                        logger.warning("Không thể map tin tức, bỏ qua.")
                        continue

                    news_scope = mapping.get("news_scope", "SPECIFIC")
                    sectors = mapping.get("sectors", [])
                    if isinstance(sectors, str):
                        sectors = [sectors]
                    raw_related = mapping.get("related_tickers", [])
                    related_str = " ".join([f"#{t.strip()}" for t in raw_related if t.strip()])
                    
                    leader_ticker = mapping.get("leader_ticker")
                    if leader_ticker:
                        leader_ticker = str(leader_ticker).strip().upper()
                    leader_name = mapping.get("leader_name", "")
                    
                    impact = mapping.get("impact", "TRUNG LẬP ⚪")
                    magnitude = mapping.get("magnitude", "TRUNG BÌNH")
                    price_trend = mapping.get("price_trend", "Đi ngang / Phân hóa")

                    # Nguyên tắc: Nếu tin đa ngành vĩ mô, tuyệt đối không gán 1 mã leader đơn lẻ
                    if news_scope == "MULTI_SECTOR":
                        leader_ticker = None
                        leader_name = None

                    # BỘ LỌC QUẢN TRỊ DANH MỤC & DÒNG TIỀN (PORTFOLIO CAPACITY FILTER)
                    portfolio_summary = portfolio_manager.get_portfolio_summary()
                    curr_cash = portfolio_summary["cash_balance"]
                    curr_positions = portfolio_summary["positions"]
                    open_symbols = [p["symbol"].strip().upper() for p in curr_positions]
                    open_count = len(open_symbols)

                    # 2. Thu thập dữ liệu kỹ thuật thực tế nếu có Leader đơn lẻ
                    ta_data = None
                    if leader_ticker:
                        df = data_fetcher.get_stock_history(leader_ticker, days=120)
                        if df is not None and len(df) >= 20:
                            ta_data = technical_analysis.analyze_stock(df)

                    # 3. Ra quyết định đầu tư cho quỹ vốn 1 tỷ
                    decision_line, assets_line = investment_engine.make_investment_decision(
                        leader_ticker=leader_ticker,
                        leader_name=leader_name,
                        impact=impact,
                        magnitude=magnitude,
                        price_trend=price_trend,
                        ta_data=ta_data,
                        news_scope=news_scope,
                        sectors=sectors,
                        related_tickers=raw_related
                    )

                    # 4. Viết nhận định chuyên sâu
                    commentary = ai_analyzer.generate_integrated_commentary(
                        title=title,
                        summary=clean_summary,
                        news_scope=news_scope,
                        sectors=sectors,
                        related_tickers=raw_related,
                        leader_ticker=leader_ticker,
                        leader_name=leader_name,
                        impact=impact,
                        magnitude=magnitude,
                        ta_data=ta_data
                    )

                    # Tải ảnh minh họa bài báo
                    img_bytes = await download_image_bytes(img_url)

                    # 5. ĐOẠN GỐC
                    sectors_display = ", ".join(sectors) if sectors else "Thị trường chung"
                    if news_scope == "MULTI_SECTOR" or not leader_ticker:
                        caption_root = (
                            "⚡ **BẢN TIN VĨ MÔ THỊ TRƯỜNG | MACET FINANCE**\n\n"
                            f"📌 **Tin mới:** {title}\n\n"
                            f"🌐 **Phạm vi tác động:** Vĩ mô / Đa ngành\n"
                            f"🏢 **Các nhóm ngành ảnh hưởng:** {sectors_display}\n"
                            f"🔍 **Cổ phiếu tiêu biểu trong diện theo dõi:** {related_str}\n"
                            f"⚖️ **Đánh giá tác động:** {impact}\n"
                            f"💥 **Mức độ ảnh hưởng:** {magnitude}\n\n"
                            f"{decision_line}"
                        )
                    else:
                        caption_root = (
                            "⚡ **BẢN TIN DOANH NGHIỆP & NGÀNH | MACET FINANCE**\n\n"
                            f"📌 **Tin mới:** {title}\n\n"
                            f"🏢 **Ngành & Cổ phiếu liên quan:** #{sectors_display} {related_str}\n"
                            f"🎯 **Tâm điểm ảnh hưởng lớn nhất:** **#{leader_ticker}** ({leader_name})\n"
                            f"⚖️ **Đánh giá tác động:** {impact}\n"
                            f"💥 **Mức độ ảnh hưởng:** {magnitude}\n"
                            f"📈 **Dự báo xu hướng #{leader_ticker}:** {price_trend}\n\n"
                            f"{decision_line}"
                        )

                    # Đảm bảo caption không vượt 1024 ký tự
                    if len(caption_root) > 1000:
                        caption_root = caption_root[:995] + "..."

                    try:
                        if img_bytes:
                            photo = BufferedInputFile(img_bytes, filename="news_thumb.jpg")
                            try:
                                root_msg = await bot.send_photo(
                                    chat_id=config.TELEGRAM_CHANNEL_ID,
                                    photo=photo,
                                    caption=caption_root,
                                    parse_mode=ParseMode.MARKDOWN
                                )
                            except Exception as e_c_md:
                                logger.warning(f"Lỗi markdown caption ({e_c_md}), gửi bằng plain text...")
                                root_msg = await bot.send_photo(
                                    chat_id=config.TELEGRAM_CHANNEL_ID,
                                    photo=photo,
                                    caption=caption_root,
                                    parse_mode=None
                                )
                        else:
                            try:
                                root_msg = await bot.send_message(
                                    chat_id=config.TELEGRAM_CHANNEL_ID,
                                    text=caption_root,
                                    parse_mode=ParseMode.MARKDOWN
                                )
                            except Exception as e_t_md:
                                logger.warning(f"Lỗi markdown text ({e_t_md}), gửi bằng plain text...")
                                root_msg = await bot.send_message(
                                    chat_id=config.TELEGRAM_CHANNEL_ID,
                                    text=caption_root,
                                    parse_mode=None
                                )

                        orig_id = root_msg.message_id
                        log_target = f"Tâm điểm #{leader_ticker}" if leader_ticker else f"Đa ngành ({sectors_display})"
                        logger.info(f"Đã đăng tin gốc kèm ảnh (ID {orig_id}): {title} [{log_target}]")

                        # ĐÁNH DẤU ĐÃ ĐĂNG NGAY LẬP TỨC: Ngay khi tin gốc lên kênh thành công
                        db.mark_news_published(news_id, title)
                        posted_count += 1

                        # 6. ĐOẠN THỨ 2: Reply lại tin nhắn gốc kèm Phân tích chuyên sâu + 2 dòng Quyết định & Tổng tài sản
                        # Kiểm tra và đảm bảo commentary không bao giờ bị đứt đoạn hoặc quá ngắn cụt
                        if not commentary or len(commentary.strip()) < 80 or "🧠" not in commentary:
                            logger.warning(f"Commentary không đạt chuẩn ({len(commentary.strip()) if commentary else 0} ký tự), kích hoạt fallback chuyên sâu...")
                            commentary = ai_analyzer.get_fallback_commentary(
                                title=title,
                                news_scope=news_scope,
                                sectors=sectors,
                                leader_ticker=leader_ticker,
                                leader_name=leader_name
                            )

                        await asyncio.sleep(2)
                        msg_part2 = (
                            f"{commentary}\n\n"
                            f"{decision_line}\n"
                            f"{assets_line}\n\n"
                            "──────────────────\n"
                            f"📢 **Macet Finance Research**"
                        )
                        if len(msg_part2) > 4000:
                            msg_part2 = msg_part2[:3990] + "..."

                        try:
                            await bot.send_message(
                                chat_id=config.TELEGRAM_CHANNEL_ID,
                                text=msg_part2,
                                parse_mode=ParseMode.MARKDOWN,
                                reply_parameters=ReplyParameters(message_id=orig_id)
                            )
                            logger.info(f"Đã đăng đoạn 2 reply tin nhắn gốc {orig_id}")
                        except Exception as e_md:
                            logger.warning(f"Lỗi gửi reply có markdown ({e_md}). Thử lại bằng plain text...")
                            try:
                                await bot.send_message(
                                    chat_id=config.TELEGRAM_CHANNEL_ID,
                                    text=msg_part2,
                                    parse_mode=None,
                                    reply_parameters=ReplyParameters(message_id=orig_id)
                                )
                                logger.info(f"Đã đăng đoạn 2 plain text reply tin nhắn gốc {orig_id}")
                            except Exception as e_reply:
                                logger.warning(f"Lỗi reply_parameters ({e_reply}). Gửi nối tiếp không reply...")
                                try:
                                    await bot.send_message(
                                        chat_id=config.TELEGRAM_CHANNEL_ID,
                                        text=msg_part2,
                                        parse_mode=None
                                    )
                                    logger.info(f"Đã đăng đoạn 2 nối tiếp không reply")
                                except Exception as e_final:
                                    logger.error(f"Không thể gửi đoạn 2: {e_final}")

                        await asyncio.sleep(5)
                        if posted_count >= max_posts:
                            return posted_count

                    except Exception as e:
                        logger.error(f"Lỗi khi gửi bài lên kênh Telegram: {e}")

            except Exception as e:
                logger.error(f"Lỗi khi đọc feed {feed_url}: {e}")

        return posted_count

async def broadcast_stock_analysis(bot: Bot, symbol: str) -> bool:
    """
    Phân tích cổ phiếu toàn diện và đăng lên Kênh Telegram:
    - Đoạn gốc: Ảnh biểu đồ kỹ thuật + Thông số phiên
    - Đoạn thứ 2: Nhận định chuyên sâu về cung cầu & dòng tiền (Reply đoạn gốc)
    - Đoạn thứ 3: Kế hoạch giao dịch & Quản trị vốn chi tiết (Reply đoạn gốc)
    """
    symbol = symbol.strip().upper()
    df = data_fetcher.get_stock_history(symbol, days=180)
    info = data_fetcher.get_symbol_info(symbol)

    if df is None or len(df) < 30:
        logger.warning(f"Không đủ dữ liệu để phân tích mã {symbol}")
        return False

    ta_data = technical_analysis.analyze_stock(df)
    chart_buf = chart_generator.generate_candlestick_chart(df, symbol)

    if not ta_data or not chart_buf:
        return False

    stock_analysis = ai_analyzer.analyze_stock_with_ai(symbol, ta_data)

    desc = info.get("description", "") if info else ""
    exchange = info.get("exchange-traded", "") if info else ""
    signals_text = "\n".join([f"• {s}" for s in ta_data["signals"]])

    # 1. ĐOẠN GỐC: Ảnh Biểu đồ nến + Chỉ số kỹ thuật
    caption_root = (
        f"📊 **BÁO CÁO PHÂN TÍCH: #{symbol}** ({exchange})\n"
        f"_{desc}_\n\n"
        f"🎯 **Trạng thái kỹ thuật:** {ta_data['summary']}\n"
        f"💵 **Giá hiện tại:** `{ta_data['last_close']:,.2f}` ({'+' if ta_data['change_price'] >= 0 else ''}{ta_data['pct_change']:.2f}%)\n"
        f"📊 **RSI(14):** `{ta_data['rsi']:.1f}` | **Khối lượng:** `{ta_data['vol_ratio']:.1f}x` TB20\n\n"
        f"🔍 **Tín hiệu đáng chú ý:**\n{signals_text}"
    )

    try:
        photo = BufferedInputFile(chart_buf.getvalue(), filename=f"{symbol}_report.png")
        root_msg = await bot.send_photo(
            chat_id=config.TELEGRAM_CHANNEL_ID,
            photo=photo,
            caption=caption_root,
            parse_mode=ParseMode.MARKDOWN
        )
        orig_id = root_msg.message_id
        logger.info(f"Đã đăng ảnh báo cáo gốc #{symbol} (ID: {orig_id})")

        if stock_analysis:
            part1, part2 = stock_analysis

            # 2. ĐOẠN THỨ 2: Reply lại đoạn gốc (orig_id)
            if part1:
                await asyncio.sleep(2)
                await bot.send_message(
                    chat_id=config.TELEGRAM_CHANNEL_ID,
                    text=part1,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_parameters=ReplyParameters(message_id=orig_id)
                )
                logger.info(f"Đã gửi đoạn 2 reply đoạn gốc {orig_id}")

            # 3. ĐOẠN THỨ 3: Reply lại đoạn gốc (orig_id)
            if part2:
                await asyncio.sleep(2)
                msg_part3 = (
                    f"{part2}\n\n"
                    "──────────────────\n"
                    f"📢 **Macet Finance Research**"
                )
                await bot.send_message(
                    chat_id=config.TELEGRAM_CHANNEL_ID,
                    text=msg_part3,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_parameters=ReplyParameters(message_id=orig_id)
                )
                logger.info(f"Đã gửi đoạn 3 reply đoạn gốc {orig_id}")

        return True
    except Exception as e:
        logger.error(f"Lỗi đăng báo cáo cổ phiếu lên kênh: {e}")
        return False
