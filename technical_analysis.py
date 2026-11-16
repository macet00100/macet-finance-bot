import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Tính chỉ báo Relative Strength Index (RSI)"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """Tính chỉ báo MACD, Signal line và Histogram"""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def analyze_stock(df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    Phân tích kỹ thuật toàn diện từ DataFrame OHLCV.
    """
    if df is None or len(df) < 30:
        return None

    close = df["Close"]
    volume = df["Volume"]

    # 1. Đường trung bình động
    sma20 = close.rolling(window=20).mean()
    sma50 = close.rolling(window=50).mean() if len(df) >= 50 else pd.Series([np.nan] * len(df), index=df.index)

    # 2. RSI & MACD
    rsi = calculate_rsi(close, period=14)
    macd_line, signal_line, macd_hist = calculate_macd(close)

    # 3. Khối lượng TB 20 phiên
    vol_sma20 = volume.rolling(window=20).mean()

    # Dữ liệu phiên gần nhất & phiên trước
    last_close = float(close.iloc[-1])
    prev_close = float(close.iloc[-2])
    change_price = last_close - prev_close
    pct_change = (change_price / prev_close) * 100

    last_vol = float(volume.iloc[-1])
    last_vol_ma20 = float(vol_sma20.iloc[-1]) if not np.isnan(vol_sma20.iloc[-1]) else last_vol
    vol_ratio = (last_vol / last_vol_ma20) if last_vol_ma20 > 0 else 1.0

    last_rsi = float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50.0
    last_sma20 = float(sma20.iloc[-1]) if not np.isnan(sma20.iloc[-1]) else last_close
    last_sma50 = float(sma50.iloc[-1]) if not np.isnan(sma50.iloc[-1]) else None

    last_macd = float(macd_line.iloc[-1])
    last_sig = float(signal_line.iloc[-1])
    prev_macd = float(macd_line.iloc[-2])
    prev_sig = float(signal_line.iloc[-2])

    # Nhận định xu hướng
    signals = []
    score = 0  # Dương: Tích cực, Âm: Tiêu cực

    # Phân tích giá vs MA20
    if last_close > last_sma20:
        signals.append("🟢 Giá nằm TRÊN MA20 (Xu hướng ngắn hạn TĂNG)")
        score += 1
    else:
        signals.append("🔴 Giá nằm DƯỚI MA20 (Xu hướng ngắn hạn GIẢM)")
        score -= 1

    # Phân tích MA20 vs MA50
    if last_sma50 is not None:
        if last_close > last_sma50:
            signals.append("🟢 Giá nằm TRÊN MA50 (Trung hạn tích cực)")
            score += 1
        else:
            signals.append("🔴 Giá nằm DƯỚI MA50 (Trung hạn điều chỉnh)")
            score -= 1

    # Phân tích RSI
    if last_rsi >= 70:
        signals.append(f"⚠️ RSI: {last_rsi:.1f} (Vùng QUÁ MUA - Cảnh báo điều chỉnh)")
        score -= 0.5
    elif last_rsi <= 30:
        signals.append(f"🔥 RSI: {last_rsi:.1f} (Vùng QUÁ BÁN - Có thể xuất hiện nhịp hồi)")
        score += 0.5
    elif 50 <= last_rsi < 70:
        signals.append(f"🟢 RSI: {last_rsi:.1f} (Lực mua tốt, đà tăng duy trì)")
        score += 1
    else:
        signals.append(f"⚪ RSI: {last_rsi:.1f} (Lực mua yếu, đang giằng co)")

    # Phân tích MACD
    if last_macd > last_sig and prev_macd <= prev_sig:
        signals.append("🚀 MACD vừa CẮT LÊN đường Signal (Tín hiệu MUA)")
        score += 2
    elif last_macd < last_sig and prev_macd >= prev_sig:
        signals.append("🚨 MACD vừa CẮT XUỐNG đường Signal (Tín hiệu BÁN)")
        score -= 2
    elif last_macd > last_sig:
        signals.append("🟢 MACD duy trì TRÊN đường Signal")
        score += 0.5
    else:
        signals.append("🔴 MACD duy trì DƯỚI đường Signal")
        score -= 0.5

    # Phân tích Khối Lượng
    if vol_ratio >= 1.5:
        signals.append(f"💥 Khối lượng đột biến: {vol_ratio:.1f}x so với TB 20 phiên")
        if change_price > 0:
            score += 1.5
            signals.append("  👉 Dòng tiền lớn gom hàng quyết liệt!")
        else:
            score -= 1.5
            signals.append("  👉 Áp lực bán tháo/xả hàng mạnh!")
    elif vol_ratio <= 0.6:
        signals.append(f"⚪ Khối lượng thấp ({vol_ratio:.1f}x TB20) - Thanh khoản cạn kiệt")

    # Tổng kết
    if score >= 2.5:
        summary = "MUA MẠNH / TÍCH CỰC 🟢🟢"
    elif 1 <= score < 2.5:
        summary = "KHẢ QUAN / THEO DÕI MUA 🟢"
    elif -1 < score < 1:
        summary = "TRUNG LẬP / QUAN SÁT ⚪"
    elif -2.5 < score <= -1:
        summary = "TIÊU CỰC / HẠ TỶ TRỌNG 🔴"
    else:
        summary = "BÁN MẠNH / RỦI RO CAO 🔴🔴"

    return {
        "last_close": last_close,
        "prev_close": prev_close,
        "change_price": change_price,
        "pct_change": pct_change,
        "high": float(df["High"].iloc[-1]),
        "low": float(df["Low"].iloc[-1]),
        "volume": last_vol,
        "vol_ma20": last_vol_ma20,
        "vol_ratio": vol_ratio,
        "rsi": last_rsi,
        "sma20": last_sma20,
        "sma50": last_sma50,
        "macd": last_macd,
        "macd_signal": last_sig,
        "signals": signals,
        "score": score,
        "summary": summary
    }
