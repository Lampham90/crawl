import requests
import json
import time

# Dùng endpoint category và country thay vì tìm kiếm để tránh bắt buộc keyword
BASE_URL = "https://phimapi.com/v1/api"
YEAR_TEST = 2025
LIMIT_TEST = 2

def test_api(name, endpoint, params=None):
    url = f"{BASE_URL}/{endpoint}"
    headers = {"User-Agent": "Mozilla/5.0"}
    p = {"limit": LIMIT_TEST, "page": 1}
    if params: p.update(params)
    
    try:
        res = requests.get(url, params=p, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            # Kiểm tra cấu trúc data của v1/api
            items = data.get('data', {}).get('items', [])
            
            # Lọc năm thủ công nếu API endpoint quoc-gia không hỗ trợ tham số year
            filtered = [i.get('name') for i in items if str(i.get('year', '')) == str(YEAR_TEST)]
            
            if not filtered: # Nếu lọc năm gắt quá không ra, lấy đại diện phim mới nhất
                filtered = [i.get('name') for i in items[:LIMIT_TEST]]
                
            print(f"[{name}]: Lấy được {len(filtered)} phim -> {filtered}")
    except Exception as e:
        print(f"[{name}]: Lỗi kết nối -> {e}")

def main():
    print(f"--- KIỂM TRA BỘ LỌC V2 (Sử dụng Endpoint Danh mục) ---\n")

    # 1. Test Hoạt hình (Dùng endpoint thể loại)
    test_api("ANIME TỔNG", "the-loai/hoat-hinh")

    # 2. Test Quốc gia (Dùng endpoint quốc gia)
    countries = [
        ("viet-nam", "VIỆT NAM"),
        ("han-quoc", "HÀN QUỐC"),
        ("trung-quoc", "TRUNG QUỐC"),
        ("au-my", "ÂU MỸ"),
        ("thanh-lan", "THÁI LAN")
    ]

    for c_slug, c_name in countries:
        # API quoc-gia thường trả về cả bộ và lẻ, mình sẽ test lấy danh sách tổng trước
        test_api(f"QUỐC GIA: {c_name}", f"quoc-gia/{c_slug}")

    print("\n--- KẾT THÚC KIỂM TRA ---")

if __name__ == "__main__":
    main()
