import db

def seed_macro_sectors():
    db.init_db()
    sectors = [
        {
            "sector_name": "Công nghệ & Bán dẫn",
            "priority_level": "HIGH",
            "catalyst": "Tăng trưởng xuất khẩu phần mềm và chuyển đổi số AI",
            "favored_tickers": "FPT, CMG"
        },
        {
            "sector_name": "Thép & Vật liệu xây dựng",
            "priority_level": "HIGH",
            "catalyst": "Biên lợi nhuận phục hồi và sản lượng tiêu thụ thép xây dựng tăng tốc",
            "favored_tickers": "HPG, NKG"
        },
        {
            "sector_name": "Đầu tư công & Hạ tầng",
            "priority_level": "HIGH",
            "catalyst": "Quyết liệt giải ngân vốn đầu tư công các dự án cao tốc trọng điểm",
            "favored_tickers": "VCG, HHV, KSB"
        },
        {
            "sector_name": "Dầu khí & Năng lượng",
            "priority_level": "HIGH",
            "catalyst": "Triển khai chuỗi dự án khí điện Lô B và giá thuê giàn khoan neo cao",
            "favored_tickers": "PVD, PVS"
        }
    ]
    db.set_macro_priority_sectors(sectors, "2026-11-16")
    active = db.get_active_priority_sectors()
    print(f"Initialized {len(active)} active priority sectors!")
    for a in active:
        print(f"- {a['sector_name']}: {a['favored_tickers']} ({a['catalyst']})")

    # Test check
    is_p, p_info = db.check_stock_sector_priority("HPG", "Thép")
    print(f"HPG is priority: {is_p} -> {p_info['sector_name'] if is_p else ''}")

    is_p2, p_info2 = db.check_stock_sector_priority("DXG", "Bất động sản")
    print(f"DXG is priority: {is_p2}")

if __name__ == "__main__":
    seed_macro_sectors()
