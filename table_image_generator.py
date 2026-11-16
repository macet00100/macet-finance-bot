import io
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from typing import Dict, Any, List
from datetime import datetime
from zoneinfo import ZoneInfo

VIETNAM_TZ = ZoneInfo("Asia/Bangkok")

def render_portfolio_table_image(summary: Dict[str, Any], date_display: str) -> io.BytesIO:
    """
    Vẽ ảnh bảng tổng kết danh mục đầu tư chuyên nghiệp (Financial Dashboard Table).
    Chia hàng, chia cột rõ nét, màu sắc chuẩn tài chính.
    Không bị tràn hay lòi chữ/số ra ngoài biên.
    """
    initial_cap = summary["initial_capital"]
    total_assets = summary["total_assets"]
    cash = summary["cash_balance"]
    stock_val = summary["stock_value"]
    pnl_total = summary["pnl_total"]
    pnl_pct = summary["pnl_total_pct"]
    positions = summary["positions"]

    num_rows = max(len(positions), 1)
    
    # Kích thước khung hình rộng rãi (13.5 inch, DPI 150) để không bao giờ bị cắt viền
    fig_width = 13.5
    fig_height = 4.4 + (num_rows * 0.52)

    fig = plt.figure(figsize=(fig_width, fig_height), dpi=150)
    fig.patch.set_facecolor("#0a0e17")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")

    # 1. Header Title & Branding
    ax.text(0.5, 0.945, "MACET FINANCE RESEARCH", color="#3b82f6", fontsize=16, fontweight="bold", ha="center")
    ax.text(0.5, 0.900, f"BẢNG TỔNG KẾT DANH MỤC ĐẦU TƯ CUỐI PHIÊN • {date_display}", color="#cbd5e1", fontsize=11, ha="center")

    # 2. Top Summary Cards (4 Thẻ tổng quan đồng bộ lề)
    table_left = 0.025
    table_width = 0.950
    table_right = table_left + table_width  # 0.975

    card_y = 0.775
    card_h = 0.088
    card_spacing = 0.015
    card_w = (table_width - 3 * card_spacing) / 4.0  # ~0.22625

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
        cx = table_left + i * (card_w + card_spacing)
        rect = patches.FancyBboxPatch(
            (cx, card_y), card_w, card_h,
            boxstyle="round,pad=0.012,rounding_size=0.015",
            facecolor="#161f30", edgecolor="#2d3f5e", linewidth=1.2
        )
        ax.add_patch(rect)
        ax.text(cx + card_w / 2.0, card_y + card_h * 0.65, c["title"], color=c["color"], fontsize=8.5, fontweight="bold", ha="center")
        ax.text(cx + card_w / 2.0, card_y + card_h * 0.25, c["val"], color=c["val_color"], fontsize=11, fontweight="bold", ha="center")

    # 3. Main Data Table Configuration
    table_top = 0.725
    header_height = 0.050
    row_height = 0.052

    # Định nghĩa cấu trúc cột chính xác: Chiều rộng & Tọa độ tâm
    # Tổng độ rộng = 0.075 + 0.085 + 0.085 + 0.085 + 0.155 + 0.085 + 0.155 + 0.085 + 0.150 = 0.950
    col_defs = [
        {"name": "MÃ CK", "w": 0.075, "align": "center"},
        {"name": "SỐ LƯỢNG", "w": 0.085, "align": "center"},
        {"name": "GIÁ MUA", "w": 0.085, "align": "center"},
        {"name": "THỊ GIÁ", "w": 0.085, "align": "center"},
        {"name": "GIÁ TRỊ (VNĐ)", "w": 0.155, "align": "center"},
        {"name": "% TÀI SẢN", "w": 0.085, "align": "center"},
        {"name": "LÃI / LỖ (VNĐ)", "w": 0.155, "align": "center"},
        {"name": "TỶ SUẤT", "w": 0.085, "align": "center"},
        {"name": "MỤC TIÊU (TP/SL)", "w": 0.150, "align": "center"},
    ]

    # Tính toán tọa độ x_start, x_end và center của từng cột
    curr_x = table_left
    for col in col_defs:
        col["x_start"] = curr_x
        col["x_end"] = curr_x + col["w"]
        col["x_center"] = curr_x + (col["w"] / 2.0)
        curr_x += col["w"]

    # Header Bar
    header_rect = patches.Rectangle(
        (table_left, table_top - header_height), table_width, header_height,
        facecolor="#1d4ed8", edgecolor="none"
    )
    ax.add_patch(header_rect)

    for col in col_defs:
        ax.text(col["x_center"], table_top - header_height / 2.0, col["name"],
                color="#ffffff", fontsize=9, fontweight="bold", ha="center", va="center")

    # Vẽ từng dòng dữ liệu
    current_y = table_top - header_height

    if not positions:
        ax.text(0.5, current_y - 0.06, "Hiện tại danh mục đang nắm giữ 100% tiền mặt, sẵn sàng giải ngân",
                color="#94a3b8", fontsize=10.5, ha="center", va="center")
    else:
        for r_idx, pos in enumerate(positions):
            row_y = current_y - (r_idx * row_height)
            bg_color = "#161f30" if (r_idx % 2 == 0) else "#0f1624"

            # Nền hàng
            row_rect = patches.Rectangle(
                (table_left, row_y - row_height), table_width, row_height,
                facecolor=bg_color, edgecolor="none"
            )
            ax.add_patch(row_rect)

            # Đường kẻ ngang phân cách hàng
            ax.plot([table_left, table_right], [row_y - row_height, row_y - row_height],
                    color="#23324d", linewidth=0.6)

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

            text_y = row_y - (row_height / 2.0)

            # Cột 1: Mã CK
            ax.text(col_defs[0]["x_center"], text_y, f"#{sym}", color="#60a5fa", fontsize=10, fontweight="bold", ha="center", va="center")
            # Cột 2: Số lượng
            ax.text(col_defs[1]["x_center"], text_y, f"{shares:,}", color="#e2e8f0", fontsize=9.5, ha="center", va="center")
            # Cột 3: Giá mua
            ax.text(col_defs[2]["x_center"], text_y, f"{buy_price:,.2f}", color="#94a3b8", fontsize=9.5, ha="center", va="center")
            # Cột 4: Thị giá
            ax.text(col_defs[3]["x_center"], text_y, f"{curr_price:,.2f}", color="#ffffff", fontsize=9.5, fontweight="bold", ha="center", va="center")
            # Cột 5: Giá trị (VNĐ)
            ax.text(col_defs[4]["x_center"], text_y, f"{curr_val:,.0f} đ", color="#f1f5f9", fontsize=9.5, ha="center", va="center")
            # Cột 6: % Tài sản
            ax.text(col_defs[5]["x_center"], text_y, f"{alloc_pct:.1f}%", color="#38bdf8", fontsize=9.5, fontweight="bold", ha="center", va="center")
            # Cột 7: Lãi/Lỗ số tiền (VNĐ)
            ax.text(col_defs[6]["x_center"], text_y, f"{sign}{pnl_amt:,.0f} đ", color=pnl_color, fontsize=9.5, fontweight="bold", ha="center", va="center")
            # Cột 8: Lãi/Lỗ %
            ax.text(col_defs[7]["x_center"], text_y, f"{sign}{pnl_p:.2f}%", color=pnl_color, fontsize=9.5, fontweight="bold", ha="center", va="center")
            # Cột 9: TP / SL
            ax.text(col_defs[8]["x_center"], text_y, f"{tp_p:,.1f} / {sl_p:,.1f}", color="#c084fc", fontsize=9, fontweight="bold", ha="center", va="center")

    # Kẻ các đường phân cách cột dọc (Grid columns)
    table_bottom_y = current_y - (num_rows * row_height)
    for col in col_defs[:-1]:
        sep_x = col["x_end"]
        ax.plot([sep_x, sep_x], [table_bottom_y, table_top], color="#23324d", linewidth=0.7, alpha=0.7)

    # Viền bao quanh toàn bộ bảng dữ liệu
    table_total_h = table_top - table_bottom_y
    outer_border = patches.Rectangle(
        (table_left, table_bottom_y), table_width, table_total_h,
        facecolor="none", edgecolor="#3b82f6", linewidth=1.5
    )
    ax.add_patch(outer_border)

    # 4. Footer Note
    ax.text(0.5, 0.035, "Macet Finance Research • Hệ thống Quản trị Danh mục Quỹ tự động & Kỷ luật thị trường",
            color="#64748b", fontsize=8.5, ha="center")

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, facecolor=fig.get_facecolor(), edgecolor="none", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf
