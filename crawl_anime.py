import requests
import json
import time

BASE_URL = "https://phimapi.com/v1/api/nam"
YEARS = [2026, 2025]
LIMIT_TEST = 2 # Lấy mỗi loại 2 phim để test nhanh

def test_fetch(name, year, params):
    url = f"{BASE_URL}/{year}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # Hợp nhất tham số mặc định và tham số lọc
    query_params = {"page": 1, "limit": 64, "sort_field": "modified.time", "sort_type": "desc"}
    query_params.update(params)
    
    try:
        res = requests.get(url, params=query_params, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            items = data.get('data', {}).get('items', [])
            
            # Lấy đúng số lượng cần test
            results = items[:LIMIT_TEST]
            names = [i.get('name') for i in results]
            print(f"[{name} - {year}]: Tìm thấy {len(names)} phim -> {names}")
            return results
    except Exception as e:
        print(f"[{name}]: Lỗi -> {e}")
    return []

def main():
    print("--- TEST LỌC THEO ENDPOINT NĂM ---")
    
    for y in YEARS:
        # 1. Test Hoạt hình
        test_fetch("ANIME MOVIE", y, {"category": "hoat-hinh", "type_list": "phim-le"})
        test_fetch("ANIME NHẬT", y, {"category": "hoat-hinh", "country": "nhat-ban"})
        test_fetch("HH TRUNG QUỐC", y, {"category": "hoat-hinh", "country": "trung-quoc"})

        # 2. Test Quốc gia (Ví dụ Việt, Hàn, Trung, Âu Mỹ, Thái)
        mapping = [
            ("viet-nam", "VIỆT NAM"),
            ("han-quoc", "HÀN QUỐC"),
            ("trung-quoc", "TRUNG QUỐC"),
            ("au-my", "ÂU MỸ"),
            ("thanh-lan", "THÁI LAN")
        ]
        
        for c_slug, c_name in mapping:
            # Lấy 2 phim lẻ của quốc gia đó trong năm y
            test_fetch(f"LẺ {c_name}", y, {"category": "phim-le", "country": c_slug})
            # Lấy 2 phim bộ của quốc gia đó trong năm y
            test_fetch(f"BỘ {c_name}", y, {"category": "phim-bo", "country": c_slug})

    print("\n--- KẾT THÚC TEST ---")

if __name__ == "__main__":
    main()
