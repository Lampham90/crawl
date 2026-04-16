import requests
import json
import time

# Cấu hình kiểm tra đơn giản
BASE_URL = "https://phimapi.com/v1/api/danh-sach"
LIMIT_TEST = 2 # Mỗi loại lấy đúng 2 phim
YEAR_TEST = 2025

def get_test_data(type_list, params):
    url = f"{BASE_URL}/{type_list}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, params=params, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, dict) and 'data' in data:
                return data['data'].get('items', [])
    except Exception as e:
        print(f" Lỗi gọi API: {e}")
    return []

def main():
    test_results = {}
    
    # 1. Test Hoạt hình (Sử dụng category và country để lọc) 
    print("--- ĐANG TEST NHÓM HOẠT HÌNH ---")
    
    # Anime Movie (Hoạt hình + Phim lẻ)
    test_results["anime_movie"] = get_test_data("hoat-hinh", {"year": YEAR_TEST, "limit": LIMIT_TEST, "category": "phim-le"})
    
    # Anime Nhật (Hoạt hình + Nhật Bản)
    test_results["anime_nhat"] = get_test_data("hoat-hinh", {"year": YEAR_TEST, "limit": LIMIT_TEST, "country": "nhat-ban"})
    
    # HH Trung Quốc (Hoạt hình + Trung Quốc)
    test_results["hh_trung_quoc"] = get_test_data("hoat-hinh", {"year": YEAR_TEST, "limit": LIMIT_TEST, "country": "trung-quoc"})

    # 2. Test Phim Lẻ & Bộ theo Quốc gia 
    print("--- ĐANG TEST NHÓM QUỐC GIA ---")
    countries = ["viet-nam", "han-quoc", "trung-quoc", "au-my", "thanh-lan"]
    
    for country in countries:
        # Test Phim Lẻ
        key_le = f"le_{country}"
        test_results[key_le] = get_test_data("phim-le", {"year": YEAR_TEST, "limit": LIMIT_TEST, "country": country})
        
        # Test Phim Bộ
        key_bo = f"bo_{country}"
        test_results[key_bo] = get_test_data("phim-bo", {"year": YEAR_TEST, "limit": LIMIT_TEST, "country": country})

    # Hiển thị kết quả kiểm tra
    print("\n========= KẾT QUẢ TEST =========")
    for key, items in test_results.items():
        count = len(items)
        names = [i.get('name') for i in items]
        print(f"[{key}]: Tìm thấy {count} phim -> {names}")

if __name__ == "__main__":
    main()
