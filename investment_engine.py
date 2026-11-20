import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any, Optional, Tuple, List
import db
import holiday_checker
import portfolio_manager
import ai_analyzer

logger = logging.getLogger(__name__)
VIETNAM_TZ = ZoneInfo("Asia/Bangkok")

# Giới hạn quản trị đa dạng hóa danh mục quỹ 1 tỷ
MAX_PORTFOLIO_POSITIONS = 15       # Tối đa 15 mã cổ phiếu trong danh mục
BASE_MAX_STOCKS_PER_SECTOR = 2     # Tối đa 2 mã cổ phiếu cho ngành thông thường
PRIORITY_MAX_STOCKS_PER_SECTOR = 3 # Tối đa 3 mã cổ phiếu cho nhóm ngành Ưu tiên Vĩ mô

def make_investment_decision(
    leader_ticker: Optional[str] = None,
    leader_name: Optional[str] = None,
    impact: str = "TRUNG LẬP ⚪",
    magnitude: str = "TRUNG BÌNH",
    price_trend: str = "ĐI NGANG",
    ta_data: Optional[Dict[str, Any]] = None,
    news_scope: str = "SPECIFIC",
    sectors: Optional[List[str]] = None,
    related_tickers: Optional[List[str]] = None
) -> Tuple[str, str]:
    """
    Sử dụng AI suy nghĩ và ra quyết định đầu tư thực tế cho quỹ 1 tỷ:
    - KHUNG GIỜ GIAO DỊCH THỰC TẾ (HOSE/HNX):
      + Nếu sàn ĐANG MỞ CỬA (09:00 - 11:30 hoặc 13:00 - 15:00): Khớp lệnh thực tế ngay lập tức.
      + Nếu sàn ĐANG NGHỈ (Nghỉ trưa 11:30 - 13:00, Ngoài giờ, Cuối tuần, Ngày lễ):
        TUYỆT ĐỐI KHÔNG KHỚP LỆNH NGAY. Lên kế hoạch giải ngân và đưa vào hàng đợi chờ phiên tiếp theo.
    - TOP-DOWN INVESTING: Ưu tiên nhóm ngành vĩ mô dẫn dắt (6.0% - 7.5% vốn, quota 3 mã).
    - ĐA DẠNG HÓA CAO: 12 - 15 mã, khống chế trần 10% - 12%/mã.
    """
    now = datetime.now(VIETNAM_TZ)
    is_open = holiday_checker.is_market_open(now)
    session_name = holiday_checker.get_session_name(now)
    next_session_desc = holiday_checker.get_next_trading_session_desc(now)

    summary = portfolio_manager.get_portfolio_summary()
    total_assets = summary["total_assets"]
    cash = summary["cash_balance"]
    positions = summary["positions"]
    open_count = len(positions)

    primary_sector = (sectors[0] if sectors else "Thị trường").strip()

    # =========================================================================
    # TRƯỜNG HỢP 0: TIN VĨ MÔ / ĐA NGÀNH -> CHỈ THEO DÕI, KHÔNG MUA MÃ ĐƠN LẺ
    # =========================================================================
    if news_scope == "MULTI_SECTOR" or not leader_ticker or len(leader_ticker) != 3:
        tickers_str = " ".join([f"#{t}" for t in (related_tickers or [])[:6]])
        sectors_str = ", ".join(sectors) if sectors else "Đa ngành"
        decision_line = (
            f"💼 **Quyết định:** THEO DÕI THÊM {tickers_str} - Tin vĩ mô tác động đa ngành ({sectors_str}), "
            f"đưa các nhóm ngành và cổ phiếu liên quan vào danh sách quan sát, duy trì tỷ trọng tiền mặt chờ điểm giải ngân cân bằng."
        )
        assets_line = (
            f"💰 **Tổng tài sản:** `{total_assets:,.0f} VNĐ` "
            f"(Tiền mặt: `{cash:,.0f} VNĐ` | Cổ phiếu: `{summary['stock_value']:,.0f} VNĐ`)"
        )
        return decision_line, assets_line

    leader_ticker = leader_ticker.strip().upper()
    holding_pos = next((p for p in positions if p["symbol"].strip().upper() == leader_ticker), None)
    if not holding_pos:
        # Kiểm tra trực tiếp từ DB phòng trường hợp danh mục chi tiết chưa đồng bộ kịp
        db_pos = portfolio_manager.get_open_position_by_symbol(leader_ticker)
        if db_pos:
            holding_pos = {
                "id": db_pos["id"],
                "symbol": db_pos["symbol"].strip().upper(),
                "shares": db_pos["shares"],
                "buy_price": db_pos["buy_price"],
                "current_price": ta_data.get("last_close", db_pos["buy_price"]) if ta_data else db_pos["buy_price"],
                "cost_basis": db_pos["cost_basis"],
                "current_value": db_pos["shares"] * (ta_data.get("last_close", db_pos["buy_price"]) if ta_data else db_pos["buy_price"]) * 1000.0,
                "pnl_amount": (db_pos["shares"] * (ta_data.get("last_close", db_pos["buy_price"]) if ta_data else db_pos["buy_price"]) * 1000.0) - db_pos["cost_basis"],
                "pnl_pct": (((db_pos["shares"] * (ta_data.get("last_close", db_pos["buy_price"]) if ta_data else db_pos["buy_price"]) * 1000.0) - db_pos["cost_basis"]) / db_pos["cost_basis"]) * 100.0 if db_pos["cost_basis"] > 0 else 0.0,
                "take_profit_price": db_pos["take_profit_price"],
                "take_profit_pct": db_pos["take_profit_pct"],
                "stop_loss_price": db_pos["stop_loss_price"],
                "stop_loss_pct": db_pos["stop_loss_pct"],
                "sector": db_pos["sector"] if ("sector" in db_pos.keys()) else "",
                "buy_date": db_pos["buy_date"]
            }

    # Kiểm tra xem mã này đã có trong hàng đợi LỆNH CHỜ (Pending Orders) chưa
    pending_orders = db.get_pending_orders()
    pending_for_sym = next((o for o in pending_orders if o["symbol"].strip().upper() == leader_ticker), None)

    current_price = ta_data.get("last_close", 0) if ta_data else 0
    rsi = ta_data.get("rsi", 50) if ta_data else 50
    change_pct = ta_data.get("pct_change", 0) if ta_data else 0

    # Kiểm tra xem mã/ngành này có thuộc Nhóm Ngành Ưu Tiên Vĩ Mô không
    is_priority, priority_info = db.check_stock_sector_priority(leader_ticker, primary_sector)
    sector_title = priority_info.get("sector_name", primary_sector) if is_priority else primary_sector
    catalyst_text = priority_info.get("catalyst", "") if is_priority else ""

    # =========================================================================
    # TRƯỜNG HỢP 1: ĐÃ NẮM GIỮ MÃ NÀY TRONG DANH MỤC
    # =========================================================================
    if holding_pos:
        pos_id = holding_pos["id"]
        buy_price = holding_pos["buy_price"]
        shares = holding_pos["shares"]
        pnl_pct = holding_pos["pnl_pct"]
        tp_price = holding_pos["take_profit_price"]
        sl_price = holding_pos["stop_loss_price"]
        curr_val = holding_pos["current_value"]
        pos_weight = (curr_val / total_assets) * 100.0 if total_assets > 0 else 0

        # Kiểm tra trạng thái chu kỳ T+2.5 của cổ phiếu đang nắm giữ
        t_info = holiday_checker.calculate_t_plus_status(holding_pos.get("buy_date", ""))
        is_avail = t_info["is_available"]

        # A. Cắt lỗ toàn phần khẩn cấp: Tin tức rất tiêu cực
        if "TIÊU CỰC" in impact.upper() and "LỚN" in magnitude.upper():
            if not is_avail:
                decision_line = (
                    f"💼 **Quyết định (Quản trị T+):** THEO DÕI CHẶT **#{leader_ticker}** - Tin tức tiêu cực lớn, nhưng cổ phiếu hiện đang ở trạng thái "
                    f"**{t_info['status_label']}** (Dự kiến khả dụng: `{t_info['settlement_desc']}`). Theo quy chế T+2.5 của sàn, chưa thể bán ngay. "
                    f"Hệ thống đưa vào diện cảnh báo ưu tiên xử lý khi hàng về tài khoản."
                )
                assets_line = (
                    f"💰 **Tổng tài sản:** `{summary['total_assets']:,.0f} VNĐ` "
                    f"(Tiền mặt: `{summary['cash_balance']:,.0f} VNĐ` | Cổ phiếu: `{summary['stock_value']:,.0f} VNĐ`)"
                )
                return decision_line, assets_line

            if is_open:
                sell_res = portfolio_manager.sell_stock(pos_id, current_price, reason=f"CẮT LỖ KHẨN CẤP ({session_name})")
                new_summary = portfolio_manager.get_portfolio_summary()
                decision_line = (
                    f"💼 **Quyết định (Khớp lệnh {session_name}):** BÁN TOÀN PHẦN **#{leader_ticker}** ({shares:,} cp giá `{current_price:,.2f}`) - "
                    f"Cắt lỗ `{sell_res['pnl_amount']:+,.0f} VNĐ` (`{sell_res['pnl_pct']:+.2f}%`) để quản trị rủi ro, đưa vào diện theo dõi thêm."
                )
                assets_line = (
                    f"💰 **Tổng tài sản:** `{new_summary['total_assets']:,.0f} VNĐ` "
                    f"(Tiền mặt: `{new_summary['cash_balance']:,.0f} VNĐ` | Cổ phiếu: `{new_summary['stock_value']:,.0f} VNĐ`)"
                )
            else:
                db.add_pending_order(leader_ticker, "SELL_FULL", 0, current_price, note=f"Cắt lỗ khẩn cấp ({session_name})")
                decision_line = (
                    f"💼 **Quyết định (Chờ mở phiên):** Lên kế hoạch BÁN TOÀN PHẦN **#{leader_ticker}** ({shares:,} cp) "
                    f"khi sàn mở cửa ({next_session_desc}) để cắt lỗ quản trị rủi ro trước thông tin tiêu cực lớn. Lệnh đã lưu vào hàng đợi chờ khớp."
                )
                assets_line = (
                    f"💰 **Tổng tài sản:** `{summary['total_assets']:,.0f} VNĐ` "
                    f"(Tiền mặt: `{summary['cash_balance']:,.0f} VNĐ` | Cổ phiếu: `{summary['stock_value']:,.0f} VNĐ`)"
                )
            return decision_line, assets_line

        # B. Bán bớt (Hạ tỷ trọng / Hiện thực hóa lợi nhuận từng phần 50%):
        should_sell_partial = (
            (pnl_pct >= 6.0 and "TÍCH CỰC" not in impact.upper())
            or (rsi >= 68)
            or ("TIÊU CỰC" in impact.upper() and pnl_pct > 0)
        )

        if should_sell_partial and shares >= 200:
            if not is_avail:
                decision_line = (
                    f"💼 **Quyết định (Chờ T+2.5):** THEO DÕI CHỐT LỜI **#{leader_ticker}** - Đạt điều kiện hạ tỷ trọng (PnL: `{pnl_pct:+.2f}%`), "
                    f"nhưng cổ phiếu đang ở trạng thái **{t_info['status_label']}** (Dự kiến khả dụng: `{t_info['settlement_desc']}`). "
                    f"Chờ cổ phiếu về tài khoản để hiện thực hóa lợi nhuận."
                )
                assets_line = (
                    f"💰 **Tổng tài sản:** `{summary['total_assets']:,.0f} VNĐ` "
                    f"(Tiền mặt: `{summary['cash_balance']:,.0f} VNĐ` | Cổ phiếu: `{summary['stock_value']:,.0f} VNĐ`)"
                )
                return decision_line, assets_line

            if is_open:
                sell_res = portfolio_manager.sell_partial_stock(
                    symbol=leader_ticker,
                    sell_ratio=0.5,
                    current_price=current_price,
                    note=f"Bán bớt hạ tỷ trọng ({session_name}) khi PnL {pnl_pct:+.2f}%"
                )
                if sell_res:
                    new_summary = portfolio_manager.get_portfolio_summary()
                    rem_val = sell_res["rem_shares"] * current_price * 1000.0
                    rem_pct = (rem_val / new_summary["total_assets"]) * 100.0
                    
                    decision_line = (
                        f"💼 **Quyết định (Khớp lệnh {session_name}):** BÁN BỚT **#{leader_ticker}** - Bán `{sell_res['sell_shares']:,} cp` "
                        f"(Thu về `{sell_res['sell_val']:,.0f} VNĐ`, Lãi/Lỗ phần bán: `{sell_res['pnl_amount']:+,.0f} VNĐ` / `{sell_res['pnl_pct']:+.2f}%`), "
                        f"giữ lại `{sell_res['rem_shares']:,} cp` (`{rem_pct:.1f}% tài sản`), Chốt lãi mục tiêu: `{tp_price:,.2f}` / Cắt lỗ: `{sl_price:,.2f}`, theo dõi thêm."
                    )
                    assets_line = (
                        f"💰 **Tổng tài sản:** `{new_summary['total_assets']:,.0f} VNĐ` "
                        f"(Tiền mặt: `{new_summary['cash_balance']:,.0f} VNĐ` | Cổ phiếu: `{new_summary['stock_value']:,.0f} VNĐ`)"
                    )
                    return decision_line, assets_line
            else:
                db.add_pending_order(leader_ticker, "SELL_PARTIAL", 0, current_price, note=f"Bán bớt 50% ({session_name})")
                sell_half = int((shares * 0.5) // 100) * 100
                decision_line = (
                    f"💼 **Quyết định (Chờ mở phiên):** Lên kế hoạch BÁN BỚT 50% **#{leader_ticker}** (dự kiến bán `{sell_half:,} cp`) "
                    f"khi sàn mở cửa ({next_session_desc}) để hiện thực hóa một phần lợi nhuận (PnL hiện tại: `{pnl_pct:+.2f}%`). Lệnh đã lưu vào hàng đợi chờ khớp."
                )
                assets_line = (
                    f"💰 **Tổng tài sản:** `{summary['total_assets']:,.0f} VNĐ` "
                    f"(Tiền mặt: `{summary['cash_balance']:,.0f} VNĐ` | Cổ phiếu: `{summary['stock_value']:,.0f} VNĐ`)"
                )
                return decision_line, assets_line

        # C. Mua thêm gia tăng (Scale-in):
        max_weight_cap = 12.0 if is_priority else 9.0
        can_buy_more = (
            "TÍCH CỰC" in impact.upper()
            and rsi < 65
            and cash >= 30_000_000
            and current_price > 0
            and pos_weight < max_weight_cap
        )

        if can_buy_more:
            add_max = 35_000_000.0 if is_priority else 25_000_000.0
            add_amount = min(add_max, cash * 0.4)
            tag_priority = " (⭐ Ngành Ưu tiên Vĩ mô)" if is_priority else ""

            if is_open:
                buy_res = portfolio_manager.buy_more_stock(
                    symbol=leader_ticker,
                    target_amount_vnd=add_amount,
                    current_price=current_price,
                    note=f"Mua thêm ({session_name}) theo tin tức tích cực ({magnitude})"
                )
                if buy_res:
                    new_summary = portfolio_manager.get_portfolio_summary()
                    total_pos_val = buy_res["new_total_shares"] * current_price * 1000.0
                    new_pos_pct = (total_pos_val / new_summary["total_assets"]) * 100.0

                    decision_line = (
                        f"💼 **Quyết định (Khớp lệnh {session_name}):** MUA THÊM **#{leader_ticker}**{tag_priority} - Mua thêm `+{buy_res['add_shares']:,} cp` "
                        f"(`{buy_res['add_cost']:,.0f} VNĐ` tại giá `{current_price:,.2f}`), nâng vị thế lên `{buy_res['new_total_shares']:,} cp` "
                        f"(`{new_pos_pct:.1f}% tài sản`, Giá TB mới: `{buy_res['new_avg_price']:,.2f}`), Chốt lãi mục tiêu: `{buy_res['new_tp_price']:,.2f}` / "
                        f"Cắt lỗ: `{buy_res['new_sl_price']:,.2f}`, theo dõi thêm phản ứng dòng tiền."
                    )
                    assets_line = (
                        f"💰 **Tổng tài sản:** `{new_summary['total_assets']:,.0f} VNĐ` "
                        f"(Tiền mặt: `{new_summary['cash_balance']:,.0f} VNĐ` | Cổ phiếu: `{new_summary['stock_value']:,.0f} VNĐ`)"
                    )
                    return decision_line, assets_line
            else:
                db.add_pending_order(leader_ticker, "BUY_MORE", add_amount, current_price, sector=sector_title, note=f"Mua thêm ngoài giờ ({session_name})")
                est_shares = int((add_amount // (current_price * 1000.0)) // 100) * 100
                decision_line = (
                    f"💼 **Quyết định (Chờ mở phiên):** Lên kế hoạch MUA THÊM **#{leader_ticker}**{tag_priority} - "
                    f"Dự kiến mua thêm `+{est_shares:,} cp` (`{add_amount:,.0f} VNĐ` tại giá `{current_price:,.2f}`) khi sàn mở cửa ({next_session_desc}). "
                    f"Lệnh đã được lưu vào hàng đợi chờ khớp."
                )
                assets_line = (
                    f"💰 **Tổng tài sản:** `{summary['total_assets']:,.0f} VNĐ` "
                    f"(Tiền mặt: `{summary['cash_balance']:,.0f} VNĐ` | Cổ phiếu: `{summary['stock_value']:,.0f} VNĐ`)"
                )
                return decision_line, assets_line

        # D. Tiếp tục nắm giữ
        t_tag = f" | {t_info['badge']} (Khả dụng: {t_info['settlement_desc']})" if not is_avail else ""
        decision_line = (
            f"💼 **Quyết định:** TIẾP TỤC NẮM GIỮ **#{leader_ticker}** - `{shares:,} cp` (`{pos_weight:.1f}% tài sản`, "
            f"Lãi/Lỗ: `{holding_pos['pnl_amount']:+,.0f} VNĐ` / `{pnl_pct:+.2f}%`{t_tag}), Chốt lãi mục tiêu: `{tp_price:,.2f}` / "
            f"Cắt lỗ: `{sl_price:,.2f}`, theo dõi thêm."
        )
        assets_line = (
            f"💰 **Tổng tài sản:** `{summary['total_assets']:,.0f} VNĐ` "
            f"(Tiền mặt: `{summary['cash_balance']:,.0f} VNĐ` | Cổ phiếu: `{summary['stock_value']:,.0f} VNĐ`)"
        )
        return decision_line, assets_line

    # =========================================================================
    # TRƯỜNG HỢP 2: CHƯA NẮM GIỮ MÃ NÀY (XÉT MUA MỚI ĐA DẠNG HÓA VÀ ƯU TIÊN VĨ MÔ)
    # =========================================================================

    # 0. Kiểm tra nếu mã này đã có lệnh chờ giải ngân trong hàng đợi
    if pending_for_sym:
        plan_action = "MUA MỚI" if pending_for_sym["action"] == "BUY" else "MUA THÊM"
        decision_line = (
            f"💼 **Quyết định (Chờ mở phiên):** ĐÃ CÓ KẾ HOẠCH {plan_action} **#{leader_ticker}** - "
            f"Hệ thống đã lưu lệnh chờ khớp `{pending_for_sym['target_amount']:,.0f} VNĐ` khi sàn mở cửa ({next_session_desc}). "
            f"Giữ nguyên kế hoạch giải ngân đã duyệt, tiếp tục theo dõi."
        )
        assets_line = (
            f"💰 **Tổng tài sản:** `{summary['total_assets']:,.0f} VNĐ` "
            f"(Tiền mặt: `{summary['cash_balance']:,.0f} VNĐ` | Cổ phiếu: `{summary['stock_value']:,.0f} VNĐ`)"
        )
        return decision_line, assets_line

    # 1. Kiểm tra trần số lượng mã cổ phiếu toàn danh mục (tối đa 15 mã)
    if open_count >= MAX_PORTFOLIO_POSITIONS:
        decision_line = (
            f"💼 **Quyết định:** Theo dõi thêm **#{leader_ticker}** - Danh mục đã đạt tối đa "
            f"`{open_count}/{MAX_PORTFOLIO_POSITIONS}` mã cổ phiếu, ưu tiên quản trị và cơ cấu các vị thế hiện tại trước khi mở mới."
        )
        assets_line = (
            f"💰 **Tổng tài sản:** `{summary['total_assets']:,.0f} VNĐ` "
            f"(Tiền mặt: `{summary['cash_balance']:,.0f} VNĐ` | Cổ phiếu: `{summary['stock_value']:,.0f} VNĐ`)"
        )
        return decision_line, assets_line

    # 2. Kiểm tra giới hạn đa dạng hóa theo ngành (Ưu tiên vĩ mô: max 3 mã, ngành thường: max 2 mã)
    max_sector_stocks = PRIORITY_MAX_STOCKS_PER_SECTOR if is_priority else BASE_MAX_STOCKS_PER_SECTOR
    sector_positions = [
        p["symbol"] for p in positions
        if primary_sector.lower() in p.get("sector", "").lower()
        or primary_sector.lower() in p.get("note", "").lower()
        or (is_priority and sector_title.lower() in p.get("sector", "").lower())
    ]
    if len(sector_positions) >= max_sector_stocks:
        sec_symbols = ", ".join([f"#{s}" for s in sector_positions])
        decision_line = (
            f"💼 **Quyết định:** Theo dõi thêm **#{leader_ticker}** - Nhóm ngành **{primary_sector}** "
            f"đã có đủ {len(sector_positions)} đại diện trong danh mục ({sec_symbols}), ưu tiên phân bổ vốn cho các nhóm ngành khác để tối ưu đa dạng hóa."
        )
        assets_line = (
            f"💰 **Tổng tài sản:** `{summary['total_assets']:,.0f} VNĐ` "
            f"(Tiền mặt: `{summary['cash_balance']:,.0f} VNĐ` | Cổ phiếu: `{summary['stock_value']:,.0f} VNĐ`)"
        )
        return decision_line, assets_line

    # 3. Xét điều kiện Mua mới
    should_buy_new = (
        "TÍCH CỰC" in impact.upper()
        and current_price > 0
        and rsi < 70
        and cash >= 35_000_000
    )

    if should_buy_new:
        if is_priority:
            alloc_pct = 7.5 if ("LỚN" in magnitude.upper()) else 6.0
            badge = f"⭐ Ưu tiên Vĩ mô ({sector_title})"
            extra_catalyst = f" (Động lực vĩ mô: {catalyst_text})" if catalyst_text else ""
        else:
            alloc_pct = 5.0 if ("LỚN" in magnitude.upper()) else 4.0
            badge = f"{primary_sector}"
            extra_catalyst = ""

        alloc_amount = (alloc_pct / 100.0) * total_assets
        alloc_amount = min(alloc_amount, cash)

        tp_pct = 12.0
        sl_pct = 6.0

        if is_open:
            # SÀN ĐANG TRONG PHIÊN GIAO DỊCH: KHỚP LỆNH THỰC TẾ
            buy_res = portfolio_manager.buy_stock(
                symbol=leader_ticker,
                target_amount_vnd=alloc_amount,
                current_price=current_price,
                tp_pct=tp_pct,
                sl_pct=sl_pct,
                sector=sector_title,
                note=f"Mua mới ({session_name}) theo vĩ mô: {impact} ({magnitude}) | Ngành: {sector_title}"
            )

            if buy_res:
                new_summary = portfolio_manager.get_portfolio_summary()
                actual_pct = (buy_res["actual_cost"] / total_assets) * 100.0
                
                decision_line = (
                    f"💼 **Quyết định (Khớp lệnh {session_name}):** Đầu tư mới **#{leader_ticker}** [{badge}] - `{buy_res['actual_cost']:,.0f} VNĐ` - `{actual_pct:.1f}% tài sản` "
                    f"(Giá mua: `{current_price:,.2f}`){extra_catalyst}, Chốt lãi `+{tp_pct:.0f}%` (Mục tiêu: `{buy_res['tp_price']:,.2f}`) / "
                    f"Cắt lỗ `-{sl_pct:.0f}%` (Ngưỡng: `{buy_res['sl_price']:,.2f}`), theo dõi thêm phản ứng dòng tiền."
                )
                assets_line = (
                    f"💰 **Tổng tài sản:** `{new_summary['total_assets']:,.0f} VNĐ` "
                    f"(Tiền mặt: `{new_summary['cash_balance']:,.0f} VNĐ` | Cổ phiếu: `{new_summary['stock_value']:,.0f} VNĐ`)"
                )
                return decision_line, assets_line
        else:
            # SÀN ĐANG NGHỈ / NGOÀI GIỜ: LƯU LỆNH CHỜ MỞ PHIÊN, KHÔNG TRỪ TIỀN NGAY
            db.add_pending_order(
                symbol=leader_ticker,
                action="BUY",
                target_amount=alloc_amount,
                planned_price=current_price,
                sector=sector_title,
                tp_pct=tp_pct,
                sl_pct=sl_pct,
                note=f"Lên kế hoạch ngoài giờ ({session_name}) | Ngành: {sector_title}"
            )
            est_shares = int((alloc_amount // (current_price * 1000.0)) // 100) * 100
            tp_est = round(current_price * (1 + tp_pct / 100.0), 2)
            sl_est = round(current_price * (1 - sl_pct / 100.0), 2)

            decision_line = (
                f"💼 **Quyết định (Chờ mở phiên):** Lên kế hoạch đầu tư mới **#{leader_ticker}** [{badge}] - "
                f"Dự kiến giải ngân `{alloc_amount:,.0f} VNĐ` (~`{est_shares:,} cp` giá `{current_price:,.2f}`, `{alloc_pct:.1f}% tài sản`) "
                f"khi sàn mở cửa ({next_session_desc}){extra_catalyst}, Chốt lãi `+{tp_pct:.0f}%` (Mục tiêu: `{tp_est:,.2f}`) / "
                f"Cắt lỗ `-{sl_pct:.0f}%` (Ngưỡng: `{sl_est:,.2f}`). Lệnh đã được lưu vào hàng đợi chờ khớp."
            )
            assets_line = (
                f"💰 **Tổng tài sản:** `{summary['total_assets']:,.0f} VNĐ` "
                f"(Tiền mặt: `{summary['cash_balance']:,.0f} VNĐ` | Cổ phiếu: `{summary['stock_value']:,.0f} VNĐ`)"
            )
            return decision_line, assets_line

    # 4. Mặc định: Theo dõi thêm
    reason = "Chờ nhịp rung lắc kiểm định hỗ trợ"
    if "TIÊU CỰC" in impact.upper():
        reason = "Tin tức tác động tiêu cực, bảo toàn vốn"
    elif rsi >= 70:
        reason = f"RSI đang ở vùng quá mua ({rsi:.1f}), rủi ro điều chỉnh ngắn hạn"
    elif cash < 35_000_000:
        reason = "Tỷ trọng tiền mặt hiện tại thấp, ưu tiên quản trị danh mục"

    decision_line = (
        f"💼 **Quyết định:** Theo dõi thêm **#{leader_ticker}** - Chưa giải ngân "
        f"(Lý do: {reason}), duy trì vị thế quan sát."
    )
    assets_line = (
        f"💰 **Tổng tài sản:** `{summary['total_assets']:,.0f} VNĐ` "
        f"(Tiền mặt: `{summary['cash_balance']:,.0f} VNĐ` | Cổ phiếu: `{summary['stock_value']:,.0f} VNĐ`)"
    )
    return decision_line, assets_line
