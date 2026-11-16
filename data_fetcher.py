import time
import httpx
import pandas as pd
import feedparser
from datetime import datetime
from typing import Optional, Dict, List, Any

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_symbol_info(symbol: str) -> Optional[Dict[str, Any]]:
    """Lấy thông tin cơ bản của mã chứng khoán (tên cty, sàn...)"""
    symbol = symbol.strip().upper()
    url = f"https://dchart-api.vndirect.com.vn/dchart/symbols?symbol={symbol}"
    try:
        with httpx.Client(timeout=8.0, headers=HEADERS) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                if "name" in data:
                    return data
    except Exception as e:
        print(f"Lỗi get_symbol_info: {e}")
    return None

def get_stock_history(symbol: str, days: int = 180, resolution: str = "D") -> Optional[pd.DataFrame]:
    """
    Lấy dữ liệu nến lịch sử (OHLCV) từ VNDirect Dchart API.
    - symbol: Mã cổ phiếu (VD: HPG, VNM, SSI)
    - days: Số ngày lịch sử
    - resolution: 'D' (ngày), 'W' (tuần), '1' (phút), '15' (15 phút)...
    """
    symbol = symbol.strip().upper()
    now = int(time.time())
    start = now - (days * 86400)
    
    url = f"https://dchart-api.vndirect.com.vn/dchart/history?resolution={resolution}&symbol={symbol}&from={start}&to={now}"
    
    try:
        with httpx.Client(timeout=10.0, headers=HEADERS) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return None
            data = resp.json()
            
            if data.get("s") != "ok" or not data.get("t"):
                return None
                
            df = pd.DataFrame({
                "Open": data["o"],
                "High": data["h"],
                "Low": data["l"],
                "Close": data["c"],
                "Volume": data["v"]
            }, index=pd.to_datetime(data["t"], unit="s"))
            
            df.index.name = "Date"
            return df
    except Exception as e:
        print(f"Lỗi get_stock_history ({symbol}): {e}")
        return None

def get_latest_news(limit: int = 5) -> List[Dict[str, str]]:
    """Lấy tin tức thị trường chứng khoán mới nhất từ CafeF RSS."""
    rss_url = "https://cafef.vn/thi-truong-chung-khoan.rss"
    articles = []
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:limit]:
            articles.append({
                "title": entry.title,
                "link": entry.link,
                "published": entry.published if hasattr(entry, "published") else ""
            })
    except Exception as e:
        print(f"Lỗi get_latest_news: {e}")
    return articles

def get_stock_news(symbol: str, limit: int = 3) -> List[Dict[str, str]]:
    """Lấy tin tức liên quan đến mã chứng khoán từ CafeF RSS."""
    symbol = symbol.strip().upper()
    rss_urls = [
        "https://cafef.vn/thi-truong-chung-khoan.rss",
        "https://cafef.vn/doanh-nghiep.rss"
    ]
    matched = []
    try:
        for url in rss_urls:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                text_to_check = f"{entry.title} {getattr(entry, 'summary', '')}".upper()
                if symbol in text_to_check:
                    matched.append({
                        "title": entry.title,
                        "link": entry.link,
                        "published": entry.published if hasattr(entry, "published") else ""
                    })
                    if len(matched) >= limit:
                        return matched
    except Exception as e:
        print(f"Lỗi get_stock_news ({symbol}): {e}")
    return matched
