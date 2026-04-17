import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor

# --- CẤU HÌNH TEST ---
BASE_URL = "https://phimapi.com/v1/api"
YEARS = [2026, 2025, 2024]
TARGET_COUNT = 15
MAX_WORKERS = 3
TEST_FILE = "data_test_lang.json"

def get_data(url, params=None):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        res = requests.get(url, params=params, timeout=15)
        if res.status_code == 200: return res.json()
    except: pass
    return None

def fetch_detail(slug):
    # API chi tiết vẫn dùng endpoint cũ
    return get_data(f"https://phimapi.com/phim/{slug}")

def fetch_by_lang(lang_code, lang_name):
    """
    lang_code: 'long-tieng' hoặc 'thuyet-minh'
    """
    results = []
    local_seen = set()
    print(f"\n[Săn tìm] Phim {lang_name} (Sử dụng API lọc theo năm)...")

    for year in YEARS:
        if len(results) >= TARGET_COUNT: break
        
        # Dùng API theo năm để lọc chính xác ngôn ngữ
        # GET https://phimapi.com/v1/api/nam/{year}
        url = f"{BASE_URL}/nam/{year}"
        params = {
            "page": 1,
            "sort_field": "modified.time",
            "sort_type": "desc",
            "sort_lang": lang_code,
            "limit": 64
        }
        
        data = get_data(url, params)
        if not data or 'data' not in data or not data['data'].get('items'):
            continue
            
        items = data['data']['items']
        # Chỉ lấy những slug chưa có trong list
        slugs_to_fetch = [item['slug'] for item in items if item['slug'] not in local_seen]
        
        if not slugs_to_fetch: continue

        # Lấy chi tiết để có đủ thông tin thumb, poster, tập phim...
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            details = list(executor.map(fetch_detail, slugs_to_fetch))

        for detail in details:
            if len(results) >= TARGET_COUNT: break
            if not detail or 'movie' not in detail: continue
            
            m = detail['movie']
            # Mặc dù API đã lọc, tui vẫn check lại cho chắc cú
            lang = str(m.get('lang', ''))
            
            results.append({
                "name": m.get('name'),
                "year": m.get('year'),
                "slug": m.get('slug'),
                "thumb": m.get('thumb_url'),
                "poster": m.get('poster_url'),
                "sub_type": lang_name,
                "current_episode": m.get('episode_current', 'Full'),
                "total_episodes": str(m.get('episode_total', '1')),
                "country": m.get('country', [{}])[0].get('name', ''),
                "lang_raw": lang
            })
            local_seen.add(m.get('slug'))
            
        print(f"  + Năm {year}: Đã lấy {len(results)}/{TARGET_COUNT}")
        time.sleep(0.5)

    return results

def main():
    start_time = time.time()
    test_data = {}

    # Chạy test riêng 2 mục
    test_data["long_tieng"] = fetch_by_lang("long-tieng", "Lồng Tiếng")
    test_data["thuyet_minh"] = fetch_by_lang("thuyet-minh", "Thuyết Minh")

    # Lưu file test
    with open(TEST_FILE, "w", encoding="utf-8") as f:
        json.dump(test_data, f, ensure_ascii=False, indent=4)

    print(f"\n[XONG] Đã tạo file {TEST_FILE}")
    print(f"Thời gian test: {int(time.time() - start_time)}s")

if __name__ == "__main__":
    main()
