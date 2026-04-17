import requests
import json
import time
import os
from concurrent.futures import ThreadPoolExecutor

# --- CẤU HÌNH ---
BASE_URL = "https://phimapi.com/v1/api"
# Quét từ 2026 lùi về 2010
YEAR_RANGE = list(range(2026, 2009, -1)) 
# Mỗi loại lấy 500 phim cho kho tổng hợp
LIMIT_PER_LANG = 500 
MAX_WORKERS = 3
# ĐÂY LÀ TÊN FILE SẼ LƯU
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
    print(f"\n[BẮT ĐẦU] Đang xây dựng kho phim {lang_name}...")

    for year in YEAR_RANGE:
        if len(results) >= LIMIT_PER_LANG: break
        
        url = f"{BASE_URL}/nam/{year}"
        params = {
            "page": 1, 
            "sort_lang": lang_code,
            "sort_field": "modified.time",
            "sort_type": "desc",
            "limit": 64 
        }
        
        data = get_data(url, params)
        if not data or 'data' not in data or not data['data'].get('items'):
            continue
            
        items = data['data']['items']
        slugs_to_fetch = [it['slug'] for it in items if it['slug'] not in seen_slugs]
        
        if not slugs_to_fetch: continue

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

        print(f"  > Năm {year}: Đã hốt được {len(results)} phim {lang_name}")
        time.sleep(0.5)

    return results

def main():
    start_time = time.time()
    library_data = {}

    # 1. Quét kho Lồng Tiếng
    library_data["all_long_tieng"] = crawl_entire_library("long-tieng", "Lồng Tiếng")
    
    # 2. Quét kho Thuyết Minh
    library_data["all_thuyet_minh"] = crawl_entire_library("thuyet-minh", "Thuyết Minh")

    # 3. LƯU DỮ LIỆU VÀO FILE JSON (Đoạn này nè ní!)
    print(f"\n[Hệ thống] Đang ghi dữ liệu vào file: {OUTPUT_FILE}...")
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(library_data, f, ensure_ascii=False, indent=4)
        print(f"✅ Đã lưu file thành công!")
    except Exception as e:
        print(f"❌ Lỗi khi lưu file: {e}")

    # 4. Tổng kết
    total_films = len(library_data["all_long_tieng"]) + len(library_data["all_thuyet_minh"])
    duration = int(time.time() - start_time)
    print(f"\n" + "="*40)
    print(f" TỔNG KẾT QUÉT THƯ VIỆN")
    print(f" - Tổng phim: {total_films}")
    print(f" - Thời gian: {duration // 60} phút {duration % 60} giây")
    print(f" - Tên file: {OUTPUT_FILE}")
    print("="*40)

if __name__ == "__main__":
    main()
