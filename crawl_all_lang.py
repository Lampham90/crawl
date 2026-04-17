import requests
import json
import time
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# --- CẤU HÌNH RÚT GỌN ---
BASE_URL = "https://phimapi.com/v1/api"
YEAR_RANGE = [2026, 2025, 2024] 
LIMIT_PER_SECTION = 400 # Giảm xuống 400 cho nhẹ và nhanh
MAX_WORKERS = 3
OUTPUT_FILE = "data_all_lang_library.json"

# Danh sách ní yêu cầu
CATEGORIES = [
    {"name": "Kinh Dị", "slug": "kinh-di"},
    {"name": "Hài Hước", "slug": "hai-huoc"},
    {"name": "Hoạt Hình", "slug": "hoat-hinh"},
    {"name": "Chiếu Rạp", "slug": "phim-chiu-rap"} # Cách gọi phim chiếu rạp
]

COUNTRIES = [
    {"name": "Hàn Quốc", "slug": "han-quoc"},
    {"name": "Trung Quốc", "slug": "trung-quoc"},
    {"name": "Âu Mỹ", "slug": "au-my"},
    {"name": "Nhật Bản", "slug": "nhat-ban"},
    {"name": "Thái Lan", "slug": "thai-lan"},
    {"name": "Việt Nam", "slug": "viet-nam"}
]

def get_data(url, params=None):
    headers = {"User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(100, 110)}.0.0.0 Safari/537.36"}
    try:
        res = requests.get(url, params=params, timeout=20)
        if res.status_code == 200: return res.json()
    except: pass
    return None

def fetch_detail(slug):
    return get_data(f"https://phimapi.com/phim/{slug}")

def crawl_by_filter(filter_type, slug, display_name):
    results = []
    seen = set()
    print(f"> Đang hốt: {display_name}...")

    for year in YEAR_RANGE:
        if len(results) >= LIMIT_PER_SECTION: break
        url = f"{BASE_URL}/nam/{year}"
        params = {"page": 1, "limit": 64, "sort_field": "modified.time", "sort_type": "desc"}
        
        if filter_type == 'the-loai': params['category'] = slug
        if filter_type == 'quoc-gia': params['country'] = slug
        if filter_type == 'lang': params['sort_lang'] = slug

        data = get_data(url, params)
        if not data or 'data' not in data or not data['data'].get('items'): continue
            
        items = data['data']['items']
        slugs = [it['slug'] for it in items if it['slug'] not in seen]
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            details = list(executor.map(fetch_detail, slugs))

        for detail in details:
            if len(results) >= LIMIT_PER_SECTION: break
            if not detail or 'movie' not in detail: continue
            m = detail['movie']
            
            # Gán nhãn sub_type
            sub_val = display_name if filter_type == 'lang' else ("Thuyết Minh" if "Thuyết Minh" in str(m.get('lang')) else "Vietsub")
            
            results.append({
                "name": m.get('name'),
                "year": m.get('year'),
                "slug": m.get('slug'),
                "thumb": m.get('thumb_url'),
                "poster": m.get('poster_url'),
                "sub_type": sub_val,
                "current_episode": m.get('episode_current', 'Full'),
                "total_episodes": str(m.get('episode_total', '1')),
                "country": m.get('country', [{}])[0].get('name', '')
            })
            seen.add(m.get('slug'))
        time.sleep(random.uniform(1, 2))
    return results

def main():
    start_time = time.time()
    final_library = {"long_tieng": [], "thuyet_minh": [], "phim_bo": [], "the_loai": {}, "quoc_gia": {}}
    report = []

    # 1. Lồng Tiếng & Thuyết Minh
    final_library["long_tieng"] = crawl_by_filter('lang', 'long-tieng', 'Lồng Tiếng')
    final_library["thuyet_minh"] = crawl_by_filter('lang', 'thuyet-minh', 'Thuyết Minh')
    
    # 2. Phim Bộ (Lấy chung từ danh sách phim bộ mới nhất)
    final_library["phim_bo"] = crawl_by_filter('the-loai', 'phim-bo', 'Phim Bộ')

    # 3. Thể Loại (Kinh dị, Hài, Hoạt hình, Chiếu rạp)
    for cat in CATEGORIES:
        res = crawl_by_filter('the-loai', cat['slug'], cat['name'])
        final_library["the_loai"][cat['slug']] = res
        report.append(f"| {cat['name']:22} | {len(res):16} |")

    # 4. Quốc Gia
    for cou in COUNTRIES:
        res = crawl_by_filter('quoc-gia', cou['slug'], cou['name'])
        final_library["quoc_gia"][cou['slug']] = res
        report.append(f"| {cou['name']:22} | {len(res):16} |")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_library, f, ensure_ascii=False, indent=4)

    print("\n" + "="*45)
    print(f"   BÁO CÁO RÚT GỌN - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("="*45)
    for line in report: print(line)
    print("="*45)
    print(f"Xong trong: {int(time.time() - start_time)//60} phút.")

if __name__ == "__main__":
    main()
