import requests
import json
import time

# Sử dụng endpoint tìm kiếm để lọc sâu
SEARCH_URL = "https://phimapi.com/v1/api/tim-kiem"
YEAR_TEST = 2025 # Test năm 2025 cho nhiều phim
LIMIT_TEST = 2

def test_filter(name, params):
    headers = {"User-Agent": "Mozilla/5.0"}
    # Keyword để trống hoặc dùng dấu cách nếu API bắt buộc, 
    # nhưng thường dùng params lọc là đủ
    params.update({"keyword": " ", "limit": LIMIT_TEST, "year": YEAR_TEST})
    
    try:
        res = requests.get(SEARCH_URL, params=params, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            items = data.get('data', {}).get('items', [])
            movie_names = [i.get('name') for i in items]
            print(f"[{name}]: Lọc được {len(movie_names)} phim -> {movie_names}")
            return items
    except Exception as e:
        print(f"[{name}]: Lỗi -> {e}")
    return []

def main():
    print(f"--- ĐANG KIỂM TRA BỘ LỌC API (NĂM {YEAR_TEST}) ---\n")

    # 1. Test Hoạt hình
    test_filter("ANIME MOVIE", {"category": "hoat-hinh", "sort_lang": "vietsub"}) # Lấy đại diện
    test_filter("ANIME NHẬT", {"category": "hoat-hinh", "country": "nhat-ban"})
    test_filter("HH TRUNG QUỐC", {"category": "hoat-hinh", "country": "trung-quoc"})

    # 2. Test Quốc gia (Lẻ & Bộ)
    countries = [
        ("viet-nam", "VIỆT NAM"),
        ("han-quoc", "HÀN QUỐC"),
        ("trung-quoc", "TRUNG QUỐC"),
        ("au-my", "ÂU MỸ"),
        ("thanh-lan", "THÁI LAN")
    ]

    for c_slug, c_name in countries:
        test_filter(f"PHIM LẺ {c_name}", {"category": "phim-le", "country": c_slug})
        test_filter(f"PHIM BỘ {c_name}", {"category": "phim-bo", "country": c_slug})

    print("\n--- KẾT THÚC KIỂM TRA ---")

if __name__ == "__main__":
    main()
