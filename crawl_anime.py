import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor

# --- CẤU HÌNH ---
BASE_URL = "https://phimapi.com/v1/api"
# Quét từ năm hiện tại lùi về năm 2010 (hoặc sâu hơn tùy ní)
YEAR_RANGE = list(range(2026, 2009, -1)) 
LIMIT_PER_LANG = 300 # Giới hạn lấy 300 phim mỗi loại để tránh file quá nặng
MAX_WORKERS = 5
OUTPUT_FILE = "data_all_lang_library.json"

def get_data(url, params=None):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        res = requests.get(url, params=params, timeout=20)
        if res.status_code == 200: return res.json()
    except: pass
    return None

def fetch_detail(slug):
    return get_data(f"https://phimapi.com/phim/{slug}")

def crawl_entire_library(lang_code, lang_name):
    results = []
    seen_slugs = set()
    print(f"\n[BẮT ĐẦU] Quét toàn bộ kho phim {lang_name}...")

    for year in YEAR_RANGE:
        if len(results) >= LIMIT_PER_LANG: break
        
        # Gọi API theo năm kết hợp lọc ngôn ngữ
        url = f"{BASE_URL}/nam/{year}"
        params = {
            "page": 1,
            "sort_field": "modified.time",
            "sort_type": "desc",
            "sort_lang": lang_code,
            "limit": 64 # Lấy tối đa 1 trang mỗi năm để đa dạng phim
        }
        
        data = get_data(url, params)
        if not data or 'data' not in data or not data['data'].get('items'):
            continue
            
        items = data['data']['items']
        slugs_to_fetch = [it['slug'] for it in items if it['slug'] not in seen_slugs]
        
        if not slugs_to_fetch: continue

        # Lấy chi tiết song song
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            details = list(executor.map(fetch_detail, slugs_to_fetch))

        for detail in details:
            if len(results) >= LIMIT_PER_LANG: break
            if not detail or 'movie' not in detail: continue
            
            m = detail['movie']
            results.append({
                "name": m.get('name'),
                "year": m.get('year'),
                "slug": m.get('slug'),
                "thumb": m.get('thumb_url'),
                "poster": m.get('poster_url'),
                "sub_type": lang_name,
                "current_episode": m.get('episode_current', 'Full'),
                "total_episodes": str(m.get('episode_total', '1')),
                "country": m.get('country', [{}])[0].get('name', '')
            })
            seen_slugs.add(m.get('slug'))

        print(f"  > Năm {year}: Đã gom {len(results)} phim {lang_name}")
        time.sleep(1) # Nghỉ lâu hơn tí vì đây là quét diện rộng

    return results

def main():
    start_time = time.time()
    library_data = {}

    # Quét cả 2 kho
    library_data["all_long_tieng"] = crawl_entire_library("long-tieng", "Lồng Tiếng")
    library_data["all_thuyet_minh"] = crawl_entire_library("thuyet-minh", "Thuyết Minh")

    # Lưu file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(library_data, f, ensure_ascii=False, indent=4)

    total_time = int(time.time() - start_time)
    print(f"\n[HOÀN THÀNH] Đã hốt xong {len(library_data['all_long_tieng']) + len(library_data['all_thuyet_minh'])} phim.")
    print(f"Thời gian thực hiện: {total_time // 60} phút {total_time % 60} giây.")

if __name__ == "__main__":
    main()
