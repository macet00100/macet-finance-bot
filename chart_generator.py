import io
import pandas as pd
import mplfinance as mpf
from typing import Optional

def generate_candlestick_chart(df: pd.DataFrame, symbol: str, num_candles: int = 60) -> Optional[io.BytesIO]:
    """
    Tạo ảnh biểu đồ nến kỹ thuật kèm Volume và MA20, MA50.
    Trả về BytesIO buffer chứa ảnh PNG.
    """
    if df is None or len(df) < 20:
        return None

    symbol = symbol.strip().upper()
    df_plot = df.tail(num_candles).copy()

    # Tùy chỉnh màu sắc theo chuẩn bảng điện Việt Nam (Xanh lá - Đỏ)
    mc = mpf.make_marketcolors(
        up="#26a69a",
        down="#ef5350",
        edge="inherit",
        wick="inherit",
        volume="in"
    )

    style = mpf.make_mpf_style(
        base_mpf_style="nightclouds",
        marketcolors=mc,
        gridstyle=":",
        gridcolor="#2c3240",
        facecolor="#131722",
        figcolor="#131722",
        rc={
            "font.family": "DejaVu Sans",
            "axes.labelcolor": "#d1d4dc",
            "xtick.color": "#d1d4dc",
            "ytick.color": "#d1d4dc"
        }
    )

    buf = io.BytesIO()
    
    # Vẽ nến + khối lượng + đường MA20, MA50
    mpf.plot(
        df_plot,
        type="candle",
        volume=True,
        mav=(20, 50),
        mavcolors=["#f39c12", "#2980b9"], # MA20 vàng cam, MA50 xanh dương
        style=style,
        title=f"\nBiểu Đồ Kỹ Thuật: {symbol} (Khung Ngày)",
        datetime_format="%d/%m",
        figsize=(10, 6),
        savefig=dict(fname=buf, dpi=120, bbox_inches="tight")
    )
    
    buf.seek(0)
    return buf
