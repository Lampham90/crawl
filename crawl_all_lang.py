import requests
import json
import time
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# --- CẤU HÌNH ---
BASE_URL = "https://phimapi.com/v1/api"
# Quét sâu từ 2026 về 2010 để lấy đủ 500 phim
YEAR_RANGE = list(range(2026, 2009, -1)) 
LIMIT_PER_SECTION = 500 
MAX_WORKERS = 3
OUTPUT_FILE = "data_all_lang_library.json"

# Danh sách slug Thể loại và Quốc gia
CATEGORIES = [
    {"name": "Hành Động", "slug": "hanh-dong"},
    {"name": "Cổ Trang", "slug": "co-trang"},
    {"name": "Chiến Tranh", "slug": "chien-tranh"},
    {"name": "Viễn Tưởng", "slug": "vien-tuong"},
    {"name": "Kinh Dị", "slug": "kinh-di"},
    {"name": "Tâm Lý", "slug": "tam-ly"},
    {"name": "Hài Hước", "slug": "hai-huoc"},
    {"name": "Hoạt Hình", "slug": "hoat-hinh"}
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
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
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
    print(f"\n> Đang thu thập: {display_name}...")

    for year in YEAR_RANGE:
        if len(results) >= LIMIT_PER_SECTION: break
        
        url = f"{BASE_URL}/nam/{year}"
        params = {
            "page": 1,
            "limit": 64,
            "sort_field": "modified.time",
            "sort_type": "desc"
        }
        if filter_type == 'the-loai': params['category'] = slug
        if filter_type == 'quoc-gia': params['country'] = slug
        if filter_type == 'lang': params['sort_lang'] = slug

        data = get_data(url, params)
        if not data or 'data' not in data or not data['data'].get('items'): continue
            
        items = data['data']['items']
        slugs_to_fetch = [it['slug'] for it in items if it['slug'] not in seen]
        
        if not slugs_to_fetch: continue

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            details = list(executor.map(fetch_detail, slugs_to_fetch))

        for detail in details:
            if len(results) >= LIMIT_PER_SECTION: break
            if not detail or 'movie' not in detail: continue
            
            m = detail['movie']
            # FIX LỖI sub_type: Hiển thị đúng loại đang quét
            sub_display = display_name if filter_type == 'lang' else ("Thuyết Minh" if "Thuyết Minh" in str(m.get('lang')) else "Vietsub")
            
            results.append({
                "name": m.get('name'),
                "year": m.get('year'),
                "slug": m.get('slug'),
                "thumb": m.get('thumb_url'),
                "poster": m.get('poster_url'),
                "sub_type": sub_display,
                "current_episode": m.get('episode_current', 'Full'),
                "total_episodes": str(m.get('episode_total', '1')),
                "country": m.get('country', [{}])[0].get('name', '')
            })
            seen.add(m.get('slug'))
        
        print(f"  + Năm {year}: Đã lấy {len(results)}/{LIMIT_PER_SECTION}")
        time.sleep(0.5)
    return results

def main():
    start_time = time.time()
    final_library = {
        "all_long_tieng": [],
        "all_thuyet_minh": [],
        "the_loai": {},
        "quoc_gia": {}
    }
    report = []

    # 1. Quét kho Lồng Tiếng & Thuyết Minh (500 phim/loại)
    res_lt = crawl_by_filter('lang', 'long-tieng', 'Lồng Tiếng')
    final_library["all_long_tieng"] = res_lt
    report.append(f"| {'Lồng Tiếng':22} | {len(res_lt):16} |")

    res_tm = crawl_by_filter('lang', 'thuyet-minh', 'Thuyết Minh')
    final_library["all_thuyet_minh"] = res_tm
    report.append(f"| {'Thuyết Minh':22} | {len(res_tm):16} |")

    # 2. Quét Thể Loại (500 phim/loại)
    for cat in CATEGORIES:
        res = crawl_by_filter('the-loai', cat['slug'], cat['name'])
        final_library["the_loai"][cat['slug']] = res
        report.append(f"| {cat['name']:22} | {len(res):16} |")

    # 3. Quét Quốc Gia (500 phim/loại)
    for cou in COUNTRIES:
        res = crawl_by_filter('quoc-gia', cou['slug'], cou['name'])
        final_library["quoc_gia"][cou['slug']] = res
        report.append(f"| {cou['name']:22} | {len(res):16} |")

    # Lưu file
    print(f"\n[Hệ thống] Đang ghi file {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_library, f, ensure_ascii=False, indent=4)

    # IN BÁO CÁO NHƯ BẢN CRAWL MỖI NGÀY
    print("\n" + "="*45)
    print(f"   BÁO CÁO KHO TỔNG HỢP - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("="*45)
    print(f"| {'Hạng mục':22} | {'Số lượng lấy':16} |")
    print("-" * 45)
    for line in report:
        print(line)
    print("="*45)
    print(f"Tổng thời gian chạy: {int(time.time() - start_time)//60} phút.\n")

if __name__ == "__main__":
    main()
