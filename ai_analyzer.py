import json
import re
import httpx
import logging
from typing import Optional, Dict, Any, Tuple, List
import config

logger = logging.getLogger(__name__)

GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent?key={config.GEMINI_API_KEY}"

def call_gemini(prompt: str, timeout: float = 30.0) -> Optional[str]:
    """Gọi trực tiếp Google Gemini REST API"""
    if not config.GEMINI_API_KEY:
        logger.error("Chưa cấu hình GEMINI_API_KEY")
        return None

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 1000
        }
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(GEMINI_API_URL, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
            else:
                logger.error(f"Lỗi gọi API (Status {resp.status_code}): {resp.text[:300]}")
    except Exception as e:
        logger.error(f"Exception khi phân tích: {e}")
    return None

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Trích xuất dict từ chuỗi JSON (kể cả có bọc trong markdown ```json ... ```)"""
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        logger.warning(f"Không thể parse JSON từ AI output: {e}")
    return None

def analyze_news_mapping(title: str, summary: str = "") -> Optional[Dict[str, Any]]:
    """
    Bước 1: Phân tích tin tức và phân loại phạm vi:
    - Nếu là tin VĨ MÔ / ĐA NGÀNH (lãi suất, tỷ giá, GDP, chính sách vĩ mô, kinh tế toàn cầu, luật chung...):
        + news_scope: "MULTI_SECTOR"
        + TUYỆT ĐỐI KHÔNG ép quy về 1 mã đơn lẻ như SSI hay VCB.
        + Liệt kê các nhóm ngành ảnh hưởng và các cổ phiếu tiêu biểu liên quan để đưa vào diện THEO DÕI.
    - Nếu là tin tác động vào NGÀNH CỤ THỂ hoặc DOANH NGHIỆP CỤ THỂ:
        + news_scope: "SPECIFIC"
        + Chỉ đích danh 1 mã cổ phiếu tại VN chịu ảnh hưởng lớn nhất (leader_ticker).
    """
    prompt = f"""
Bạn là Giám đốc Nghiên cứu Đầu tư Cao cấp tại Macet Finance. Hãy phân tích tin tức sau và phân loại chính xác phạm vi tác động đối với thị trường chứng khoán Việt Nam (HOSE, HNX, UPCoM):

QUY TẮC PHÂN LOẠI PHẠM VI (news_scope):
1. ĐẶT "news_scope": "MULTI_SECTOR" (Tin Vĩ Mô / Đa Ngành):
   - Áp dụng khi: Tin tức mang tính vĩ mô chung (lãi suất NHNN, tỷ giá USD/VND, lạm phát, GDP, chính sách tiền tệ, Fed, thị trường toàn cầu, các luật hoặc gói chính sách bao quát tác động tới nhiều ngành).
   - Khi đó: TUYỆT ĐỐI KHÔNG quy về 1 mã cổ phiếu đơn lẻ (như SSI, VCB).
   - "leader_ticker": null
   - "leader_name": null
   - "sectors": Danh sách các nhóm ngành bị tác động (Ví dụ: ["Ngân hàng", "Bất động sản", "Chứng khoán", "Xuất nhập khẩu"])
   - "related_tickers": Danh sách 4-8 mã cổ phiếu tiêu biểu của các nhóm ngành đó (Ví dụ: ["VCB", "MBB", "VHM", "SSI", "VND", "VHC"])

2. ĐẶT "news_scope": "SPECIFIC" (Tin Ngành Cụ Thể hoặc Doanh Nghiệp Cụ Thể):
   - Áp dụng khi: Tin tức tác động vào 1 ngành cụ thể (VD: Thép, Dầu khí, Bán lẻ công nghệ, Thủy sản, Chăn nuôi, Cảng biển...) HOẶC tin trực tiếp về 1 doanh nghiệp cụ thể (kết quả kinh doanh, ký hợp đồng lớn, chia cổ tức, thay đổi ban lãnh đạo, dự án mới...).
   - Khi đó: BẮT BUỘC chọn 1 mã cổ phiếu đầu ngành/tâm điểm tại Việt Nam chịu ảnh hưởng lớn nhất vào "leader_ticker" (3 chữ cái in hoa, ví dụ: HPG, PVD, MWG, FPT, PNJ, DBC, VNM...).
   - "leader_name": Tên đầy đủ của công ty tâm điểm tại VN
   - "sectors": [Tên ngành cụ thể]
   - "related_tickers": 2-4 mã cùng ngành

QUY TẮC CHUNG:
- TUYỆT ĐỐI KHÔNG dùng từ "AI", "trí tuệ nhân tạo", "mô hình".
- Trả về CHÍNH XÁC định dạng JSON sau:
{{
  "news_scope": "MULTI_SECTOR" hoặc "SPECIFIC",
  "sectors": ["Tên nhóm ngành 1", "Tên nhóm ngành 2"],
  "related_tickers": ["MÃ1", "MÃ2", "MÃ3"],
  "leader_ticker": "MÃ_LỚN_NHẤT" (hoặc null nếu MULTI_SECTOR),
  "leader_name": "Tên công ty" (hoặc null nếu MULTI_SECTOR),
  "impact": "TÍCH CỰC (BULLISH 🟢)" hoặc "TIÊU CỰC (BEARISH 🔴)" hoặc "TRUNG LẬP ⚪",
  "magnitude": "LỚN (Trọng yếu)" hoặc "TRUNG BÌNH" hoặc "NHỎ",
  "price_trend": "TĂNG trong ngắn hạn" hoặc "GIẢM trong ngắn hạn" hoặc "ĐI NGANG / PHÂN HÓA"
}}

Tiêu đề tin: {title}
Nội dung tóm tắt: {summary if summary else "Không có thêm tóm tắt"}
"""
    raw_output = call_gemini(prompt)
    if not raw_output:
        return None
    return extract_json_from_text(raw_output)

def generate_integrated_commentary(
    title: str,
    summary: str,
    news_scope: str,
    sectors: List[str],
    related_tickers: List[str],
    leader_ticker: Optional[str] = None,
    leader_name: Optional[str] = None,
    impact: str = "TRUNG LẬP ⚪",
    magnitude: str = "TRUNG BÌNH",
    ta_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Bước 2: Viết bài phân tích chuyên sâu cho Đoạn 2 (Reply tin gốc):
    - Nếu là MULTI_SECTOR: Phân tích góc nhìn vĩ mô, tác động phân hóa giữa các ngành, đưa vào diện theo dõi.
    - Nếu là SPECIFIC: Kết hợp bản chất tin tức và dữ liệu kỹ thuật thực tế của mã Leader để ra chiến lược hành động.
    """
    if news_scope == "MULTI_SECTOR" or not leader_ticker:
        prompt = f"""
Bạn là Chuyên gia Chiến lược Vĩ mô tại Macet Finance. Hãy viết nhận định chuyên sâu (Đoạn 2) phân tích tác động của tin tức vĩ mô đa ngành sau:

Tin tức: {title}
Nội dung: {summary}
Các nhóm ngành liên quan: {', '.join(sectors) if sectors else 'Đa ngành'}
Cổ phiếu tiêu biểu trong diện theo dõi: {', '.join(related_tickers) if related_tickers else 'Thị trường chung'}
Đánh giá tác động sơ bộ: {impact} ({magnitude})

QUY TẮC:
- TUYỆT ĐỐI KHÔNG dùng từ "AI", "trí tuệ nhân tạo", "thuật toán".
- Phân tích cơ chế tác động và sự phân hóa: Nhóm ngành nào được hưởng lợi, nhóm ngành nào chịu áp lực/chi phí gia tăng.
- Định hướng danh mục: Đưa các nhóm ngành và cổ phiếu trên vào danh sách theo dõi (Watchlist), quan sát phản ứng dòng tiền và nhịp cân bằng trước khi giải ngân.

HÃY TRẢ VỀ ĐẦU RA THEO ĐỊNH DẠNG:
🧠 **Góc nhìn Macet Finance về diễn biến Vĩ mô:**
• [Phân tích cơ chế tác động và mức độ phân hóa dòng tiền giữa các nhóm ngành]
• [Đánh giá tác động tới thanh khoản thị trường chung và tâm lý giới đầu tư]
🎯 **Chiến lược theo dõi & Quản trị danh mục:** [Khuyến nghị các nhóm ngành và cổ phiếu ưu tiên quan sát phản ứng dòng tiền, chờ điểm cân bằng để kích hoạt giải ngân]
"""
    else:
        tech_context = ""
        if ta_data:
            signals_str = "; ".join(ta_data.get("signals", []))
            tech_context = f"""
DỮ LIỆU GIAO DỊCH THỰC TẾ HIỆN TẠI CỦA #{leader_ticker}:
- Thị giá: {ta_data.get('last_close'):,.2f} nghìn VNĐ (Biến động phiên: {ta_data.get('change_price'):+.2f}, {ta_data.get('pct_change'):+.2f}%)
- MA20: {ta_data.get('sma20'):,.2f} | MA50: {ta_data.get('sma50')}
- Chỉ số RSI(14): {ta_data.get('rsi'):.1f}
- Thanh khoản: {ta_data.get('vol_ratio'):.1f}x so với trung bình 20 phiên
- Tín hiệu kỹ thuật: {signals_str}
- Đánh giá tổng quan kỹ thuật: {ta_data.get('summary')}
"""
        else:
            tech_context = f"Mã #{leader_ticker} đang thu hút sự chú ý của dòng tiền trên sàn chứng khoán Việt Nam."

        prompt = f"""
Bạn là Chuyên gia Chiến lược Đầu tư Cao cấp tại Macet Finance. Hãy viết nhận định chuyên sâu (Đoạn 2) phân tích tác động của tin tức đối với mã cổ phiếu tâm điểm #{leader_ticker} ({leader_name}):

Tin tức: {title}
Đánh giá sơ bộ: {impact} ({magnitude})
{tech_context}

QUY TẮC:
- TUYỆT ĐỐI KHÔNG dùng từ "AI", "trí tuệ nhân tạo", "thuật toán", "tự động".
- Kết hợp nhuần nhuyễn giữa cơ chế tác động cơ bản của tin tức VÀ số liệu giá/kỹ thuật/dòng tiền thực tế ở trên để đưa ra góc nhìn thuyết phục như một chuyên gia quỹ thực thụ.
- Sử dụng thuật ngữ tài chính chuẩn xác.

HÃY TRẢ VỀ ĐẦU RA THEO ĐỊNH DẠNG:
🧠 **Góc nhìn Macet Finance về #{leader_ticker}:**
• [Phân tích cơ chế tác động cụ thể của tin tức đến doanh thu/lợi nhuận cốt lõi của #{leader_ticker} và vị thế cạnh tranh trong ngành]
• [Đánh giá phản ứng của dòng tiền lớn, thanh khoản và trạng thái cung cầu thực tế theo số liệu giá/RSI/MA20 ở trên]
🎯 **Chiến lược hành động cho #{leader_ticker}:** [Khuyến nghị cụ thể: Vùng gom tích lũy / Canh chốt lời / Vùng hỗ trợ - kháng cự cần theo dõi]
"""
    res = call_gemini(prompt)
    return res.strip() if res else ""

def analyze_stock_with_ai(symbol: str, ta_data: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    """
    Tạo báo cáo nhận định chuyên sâu cho 1 mã cổ phiếu cụ thể (khi người dùng gõ /post_ta <mã>).
    """
    prompt = f"""
Bạn là Trưởng bộ phận Phân tích Kỹ thuật tại Macet Finance. Dựa trên số liệu giao dịch của mã cổ phiếu {symbol}:
- Giá đóng cửa: {ta_data.get('last_close')} (Biến động: {ta_data.get('change_price'):+.2f}, {ta_data.get('pct_change'):+.2f}%)
- MA20: {ta_data.get('sma20'):.2f} | MA50: {ta_data.get('sma50')}
- Chỉ số RSI(14): {ta_data.get('rsi'):.1f}
- Khối lượng giao dịch: {ta_data.get('vol_ratio'):.1f}x so với trung bình 20 phiên
- Tín hiệu kỹ thuật: {'; '.join(ta_data.get('signals', []))}

QUY TẮC:
- TUYỆT ĐỐI KHÔNG dùng từ "AI", "trí tuệ nhân tạo", "máy tính", "tự động".
- Viết như một chuyên gia tư vấn giao dịch kỳ cựu.

HÃY TRẢ VỀ CHÍNH XÁC THEO ĐỊNH DẠNG SAU, CÓ DẤU `===SPLIT===` Ở GIỮA:

🧠 **Góc nhìn Macet Finance về #{symbol}:**
• [Nhận định về trạng thái cung cầu và cấu trúc giá hiện tại so với các đường MA]
• [Đánh giá thanh khoản và động thái dòng tiền lớn/dòng tiền thông minh]
===SPLIT===
🎯 **Kế hoạch hành động & Quản trị vốn:**
• **Vùng hỗ trợ/kháng cự then chốt:** [Nêu vùng giá cụ thể]
• **Chiến lược giao dịch:** [Khuyến nghị vị thế: Thăm dò / Mua gia tăng / Chốt lời / Cắt lỗ]
• **Quản trị rủi ro:** [Điểm vi phạm cần hạ tỷ trọng]
"""
    raw_text = call_gemini(prompt)
    if not raw_text:
        return None

    if "===SPLIT===" in raw_text:
        parts = raw_text.split("===SPLIT===")
        return parts[0].strip(), parts[1].strip()
    else:
        if "🎯" in raw_text:
            idx = raw_text.find("🎯")
            return raw_text[:idx].strip(), raw_text[idx:].strip()
        return raw_text, ""

def extract_macro_priority_sectors(macro_text: str) -> List[Dict[str, Any]]:
    """
    Trích xuất và xếp hạng Top các nhóm ngành có tiềm năng tăng trưởng cao nhất từ phân tích vĩ mô
    """
    prompt = f"""
Bạn là Giám đốc Chiến lược Phân bổ Tài sản tại Macet Finance. Dựa trên bản phân tích vĩ mô sau:

{macro_text}

QUY TẮC:
- Hãy chọn ra TOP 3 - 4 NHÓM NGÀNH trên thị trường chứng khoán Việt Nam (HOSE, HNX, UPCoM) có TIỀM NĂNG TĂNG TRƯỞNG CAO NHẤT, được hưởng lợi vĩ mô rõ nét nhất trong giai đoạn này (ví dụ: Đầu tư công/Xây dựng hạ tầng, Thép, Dầu khí, Công nghệ, Bán lẻ tiêu dùng, Xuất khẩu/Thủy sản, Ngân hàng...).
- Với mỗi ngành, nêu rõ lý do động lực vĩ mô (catalyst ngắn gọn 1 câu) và 2-3 mã cổ phiếu đầu ngành tiêu biểu nhất (favored_tickers, ví dụ: "HPG, NKG").
- TUYỆT ĐỐI KHÔNG dùng từ "AI", "trí tuệ nhân tạo".
- Trả về ĐÚNG định dạng JSON mảng:
[
  {{
    "sector_name": "Tên nhóm ngành",
    "priority_level": "HIGH",
    "catalyst": "Lý do hưởng lợi vĩ mô ngắn gọn",
    "favored_tickers": "MÃ1, MÃ2, MÃ3"
  }}
]
"""
    raw_output = call_gemini(prompt)
    if not raw_output:
        return []
    try:
        match = re.search(r"\[.*\]", raw_output, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        logger.warning(f"Không thể parse JSON priority sectors: {e}")
    return []
