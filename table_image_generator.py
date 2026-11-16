import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from typing import Dict, Any, List
from datetime import datetime
from zoneinfo import ZoneInfo

VIETNAM_TZ = ZoneInfo("Asia/Bangkok")

def render_portfolio_table_image(summary: Dict[str, Any], date_display: str) -> io.BytesIO:
    """
    Vẽ ảnh bảng tổng kết danh mục đầu tư chuyên nghiệp (Financial Dashboard Table):
    - Tự động co giãn theo số lượng cổ phiếu thực tế, loại bỏ hoàn toàn các khoảng trống thừa.
    - Cỡ chữ to rõ, số liệu nổi bật, vừa vặn cân đối với các ô thẻ và cột bảng.
    - Trạng thái 100% tiền mặt hiển thị banner sang trọng, không để các ô trống vô nghĩa.
    """
    initial_cap = summary["initial_capital"]
    total_assets = summary["total_assets"]
    cash = summary["cash_balance"]
    stock_val = summary["stock_value"]
    pnl_total = summary["pnl_total"]
    pnl_pct = summary["pnl_total_pct"]
    positions = summary.get("positions", [])

    fig_w = 13.2  # Chiều rộng chuẩn 13.2 inch (1980px ở 150 DPI)
    
    # Tính toán chiều cao linh hoạt theo số dòng thực tế để KHÔNG BAO GIỜ bị thừa khoảng trống
    has_positions = len(positions) > 0
    header_h = 0.52
    row_h = 0.50
    empty_banner_h = 1.15
    
    table_content_h = (len(positions) * row_h) if has_positions else empty_banner_h
    table_total_h = header_h + table_content_h
    
    # Tổng chiều cao: Title (0.95) + Cards (1.20) + Table + Footer (0.45) + Spacers (0.75)
    fig_h = 0.95 + 1.20 + table_total_h + 0.45 + 0.75
    
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=150)
    fig.patch.set_facecolor("#0a0e17")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    
    def norm_y(y_inch):
        return y_inch / fig_h

    def norm_x(x_inch):
        return x_inch / fig_w

    def norm_h(h_inch):
        return h_inch / fig_h

    def norm_w(w_inch):
        return w_inch / fig_w

    # 1. Header Title & Branding
    title_top_inch = fig_h - 0.35
    ax.text(0.5, norm_y(title_top_inch), "MACET FINANCE RESEARCH", color="#3b82f6", fontsize=18, fontweight="bold", ha="center", va="top")
    ax.text(0.5, norm_y(title_top_inch - 0.42), f"BẢNG TỔNG KẾT DANH MỤC ĐẦU TƯ CUỐI PHIÊN • {date_display}", color="#cbd5e1", fontsize=11.5, ha="center", va="top")

    # 2. Top Summary Cards (4 Thẻ tổng quan to rõ, lấp đầy ô)
    tbl_left_inch = 0.40
    tbl_w_inch = fig_w - 2 * tbl_left_inch  # 12.4 in
    card_spacing_inch = 0.20
    card_w_inch = (tbl_w_inch - 3 * card_spacing_inch) / 4.0  # ~2.95 in
    card_h_inch = 1.15
    card_top_inch = title_top_inch - 0.85
    card_bottom_inch = card_top_inch - card_h_inch

    cards = [
        {"title": "VỐN BAN ĐẦU", "val": f"{initial_cap:,.0f} đ", "color": "#94a3b8", "val_color": "#ffffff"},
        {"title": "TỔNG TÀI SẢN", "val": f"{total_assets:,.0f} đ", "color": "#94a3b8", "val_color": "#ffffff"},
        {
            "title": "TỔNG LÃI / LỖ",
            "val": f"{'+' if pnl_total >= 0 else ''}{pnl_total:,.0f} đ ({'+' if pnl_pct >= 0 else ''}{pnl_pct:.2f}%)",
            "color": "#94a3b8",
            "val_color": "#10b981" if pnl_total >= 0 else "#ef4444"
        },
        {
            "title": "TIỀN MẶT / CỔ PHIẾU",
            "val": f"{(cash/total_assets)*100:.0f}% / {(stock_val/total_assets)*100:.0f}%",
            "color": "#94a3b8",
            "val_color": "#38bdf8"
        }
    ]

    for i, c in enumerate(cards):
        cx_inch = tbl_left_inch + i * (card_w_inch + card_spacing_inch)
        rect = patches.FancyBboxPatch(
            (norm_x(cx_inch), norm_y(card_bottom_inch)), norm_w(card_w_inch), norm_h(card_h_inch),
            boxstyle="round,pad=0.015,rounding_size=0.025",
            facecolor="#161f30", edgecolor="#2d3f5e", linewidth=1.5
        )
        ax.add_patch(rect)
        # Chữ to rõ, căn giữa ô đẹp mắt
        ax.text(norm_x(cx_inch + card_w_inch / 2.0), norm_y(card_bottom_inch + card_h_inch * 0.68),
                c["title"], color=c["color"], fontsize=11, fontweight="bold", ha="center", va="center")
        ax.text(norm_x(cx_inch + card_w_inch / 2.0), norm_y(card_bottom_inch + card_h_inch * 0.28),
                c["val"], color=c["val_color"], fontsize=15.5, fontweight="bold", ha="center", va="center")

    # 3. Main Data Table
    table_top_inch = card_bottom_inch - 0.30
    table_bottom_inch = table_top_inch - table_total_h

    col_weights = [
        ("MÃ CK", 0.08),
        ("SỐ LƯỢNG", 0.09),
        ("GIÁ MUA", 0.09),
        ("THỊ GIÁ", 0.09),
        ("GIÁ TRỊ (VNĐ)", 0.16),
        ("% TÀI SẢN", 0.09),
        ("LÃI / LỖ (VNĐ)", 0.16),
        ("TỶ SUẤT", 0.09),
        ("MỤC TIÊU (TP/SL)", 0.15)
    ]
    total_weight = sum(w for _, w in col_weights)
    
    col_defs = []
    curr_x_inch = tbl_left_inch
    for name, w_ratio in col_weights:
        w_in = tbl_w_inch * (w_ratio / total_weight)
        col_defs.append({
            "name": name,
            "x_start": curr_x_inch,
            "x_end": curr_x_inch + w_in,
            "x_center": curr_x_inch + w_in / 2.0,
            "w": w_in
        })
        curr_x_inch += w_in

    # Vẽ Header Bar
    header_bottom_inch = table_top_inch - header_h
    header_rect = patches.Rectangle(
        (norm_x(tbl_left_inch), norm_y(header_bottom_inch)), norm_w(tbl_w_inch), norm_h(header_h),
        facecolor="#1d4ed8", edgecolor="none"
    )
    ax.add_patch(header_rect)

    for col in col_defs:
        ax.text(norm_x(col["x_center"]), norm_y(header_bottom_inch + header_h / 2.0),
                col["name"], color="#ffffff", fontsize=10.5, fontweight="bold", ha="center", va="center")

    # Vẽ nội dung bảng
    if not has_positions:
        # Trường hợp 100% tiền mặt: Hiển thị banner thông báo sang trọng, không để ô trống vô nghĩa
        empty_rect = patches.Rectangle(
            (norm_x(tbl_left_inch), norm_y(table_bottom_inch)), norm_w(tbl_w_inch), norm_h(empty_banner_h),
            facecolor="#111827", edgecolor="none"
        )
        ax.add_patch(empty_rect)
        
        banner_center_y = table_bottom_inch + empty_banner_h / 2.0
        ax.text(0.5, norm_y(banner_center_y + 0.20),
                "DANH MỤC HIỆN TẠI ĐANG NẮM GIỮ 100% TIỀN MẶT (1.000.000.000 VNĐ)",
                color="#38bdf8", fontsize=13, fontweight="bold", ha="center", va="center")
        ax.text(0.5, norm_y(banner_center_y - 0.20),
                "Sẵn sàng giải ngân vào các nhóm ngành ưu tiên dẫn sóng: Công nghệ & Bán dẫn, Thép, Đầu tư công, Dầu khí",
                color="#94a3b8", fontsize=11, ha="center", va="center")
    else:
        for r_idx, pos in enumerate(positions):
            row_top_inch = header_bottom_inch - (r_idx * row_h)
            row_bottom_inch = row_top_inch - row_h
            bg_color = "#161f30" if (r_idx % 2 == 0) else "#0f1624"

            row_rect = patches.Rectangle(
                (norm_x(tbl_left_inch), norm_y(row_bottom_inch)), norm_w(tbl_w_inch), norm_h(row_h),
                facecolor=bg_color, edgecolor="none"
            )
            ax.add_patch(row_rect)

            # Phân cách ngang
            ax.plot([norm_x(tbl_left_inch), norm_x(tbl_left_inch + tbl_w_inch)],
                    [norm_y(row_bottom_inch), norm_y(row_bottom_inch)],
                    color="#23324d", linewidth=0.8)

            sym = pos["symbol"]
            shares = pos["shares"]
            buy_price = pos["buy_price"]
            curr_price = pos["current_price"]
            curr_val = pos["current_value"]
            alloc_pct = (curr_val / total_assets) * 100.0 if total_assets > 0 else 0
            pnl_amt = pos["pnl_amount"]
            pnl_p = pos["pnl_pct"]
            tp_p = pos.get("take_profit_price", 0)
            sl_p = pos.get("stop_loss_price", 0)

            pnl_color = "#10b981" if pnl_amt >= 0 else "#ef4444"
            sign = "+" if pnl_amt >= 0 else ""

            text_y_norm = norm_y(row_bottom_inch + row_h / 2.0)

            ax.text(norm_x(col_defs[0]["x_center"]), text_y_norm, f"#{sym}", color="#60a5fa", fontsize=11, fontweight="bold", ha="center", va="center")
            ax.text(norm_x(col_defs[1]["x_center"]), text_y_norm, f"{shares:,}", color="#e2e8f0", fontsize=10.5, ha="center", va="center")
            ax.text(norm_x(col_defs[2]["x_center"]), text_y_norm, f"{buy_price:,.2f}", color="#94a3b8", fontsize=10.5, ha="center", va="center")
            ax.text(norm_x(col_defs[3]["x_center"]), text_y_norm, f"{curr_price:,.2f}", color="#ffffff", fontsize=10.5, fontweight="bold", ha="center", va="center")
            ax.text(norm_x(col_defs[4]["x_center"]), text_y_norm, f"{curr_val:,.0f} đ", color="#f1f5f9", fontsize=10.5, ha="center", va="center")
            ax.text(norm_x(col_defs[5]["x_center"]), text_y_norm, f"{alloc_pct:.1f}%", color="#38bdf8", fontsize=10.5, fontweight="bold", ha="center", va="center")
            ax.text(norm_x(col_defs[6]["x_center"]), text_y_norm, f"{sign}{pnl_amt:,.0f} đ", color=pnl_color, fontsize=10.5, fontweight="bold", ha="center", va="center")
            ax.text(norm_x(col_defs[7]["x_center"]), text_y_norm, f"{sign}{pnl_p:.2f}%", color=pnl_color, fontsize=10.5, fontweight="bold", ha="center", va="center")
            ax.text(norm_x(col_defs[8]["x_center"]), text_y_norm, f"{tp_p:,.1f} / {sl_p:,.1f}", color="#c084fc", fontsize=10, fontweight="bold", ha="center", va="center")

        # Đường kẻ dọc phân chia cột
        for col in col_defs[:-1]:
            sep_x = col["x_end"]
            ax.plot([norm_x(sep_x), norm_x(sep_x)], [norm_y(table_bottom_inch), norm_y(table_top_inch)],
                    color="#23324d", linewidth=0.8, alpha=0.7)

    # Viền bao ngoài toàn bảng
    outer_border = patches.Rectangle(
        (norm_x(tbl_left_inch), norm_y(table_bottom_inch)), norm_w(tbl_w_inch), norm_h(table_total_h),
        facecolor="none", edgecolor="#3b82f6", linewidth=1.5
    )
    ax.add_patch(outer_border)

    # 4. Footer Note (Ngay sát mép dưới bảng, KHÔNG có khoảng trống thừa)
    footer_y_inch = table_bottom_inch - 0.28
    ax.text(0.5, norm_y(footer_y_inch), "Macet Finance Research • Hệ thống Quản trị Danh mục Quỹ tự động & Kỷ luật thị trường",
            color="#64748b", fontsize=9.5, ha="center", va="center")

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, facecolor=fig.get_facecolor(), edgecolor="none", bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    buf.seek(0)
    return buf
