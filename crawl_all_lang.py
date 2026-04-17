import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor

# --- CẤU HÌNH ---
BASE_URL = "https://phimapi.com/v1/api"
YEARS = [2026, 2025, 2024] # Với thể loại, mình ưu tiên phim mới cho chất lượng
LIMIT_PER_SECTION = 100 
MAX_WORKERS = 3
OUTPUT_FILE = "data_all_lang_library.json"

# Danh sách slug Thể loại và Quốc gia ní muốn lấy (có thể thêm bớt tùy ý)
CATEGORIES = [
    {"name": "Hành Động", "slug": "hanh-dong"},
    {"name": "Cổ Trang", "slug": "co-trang"},
    {"name": "Chiến Tranh", "slug": "chien-tranh"},
    {"name": "Viễn Tưởng", "slug": "vien-tuong"},
    {"name": "Kinh Dị", "slug": "kinh-di"},
    {"name": "Tâm Lý", "slug": "tam-ly"}
]

COUNTRIES = [
    {"name": "Hàn Quốc", "slug": "han-quoc"},
    {"name": "Trung Quốc", "slug": "trung-quoc"},
    {"name": "Âu Mỹ", "slug": "au-my"},
    {"name": "Nhật Bản", "slug": "nhat-ban"},
    {"name": "Thái Lan", "slug": "thai-lan"}
]

def get_data(url, params=None):
    try:
        res = requests.get(url, params=params, timeout=20)
        if res.status_code == 200: return res.json()
    except: pass
    return None

def fetch_detail(slug):
    return get_data(f"https://phimapi.com/phim/{slug}")

def crawl_by_filter(filter_type, slug, display_name):
    """
    filter_type: 'nam', 'the-loai', 'quoc-gia'
    """
    results = []
    seen = set()
    print(f"> Đang hốt mục: {display_name}...")

    # Quét qua các năm để đảm bảo có phim mới nhất cho thể loại đó
    for year in YEARS:
        if len(results) >= LIMIT_PER_SECTION: break
        
        # Dùng API Năm kết hợp lọc category/country
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
        slugs = [it['slug'] for it in items if it['slug'] not in seen]
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            details = list(executor.map(fetch_detail, slugs))

        for detail in details:
            if len(results) >= LIMIT_PER_SECTION: break
            if not detail or 'movie' not in detail: continue
            m = detail['movie']
            results.append({
                "name": m.get('name'),
                "year": m.get('year'),
                "slug": m.get('slug'),
                "thumb": m.get('thumb_url'),
                "poster": m.get('poster_url'),
                "sub_type": "Thuyết Minh" if "Thuyết Minh" in str(m.get('lang')) else "Vietsub",
                "current_episode": m.get('episode_current', 'Full'),
                "country": m.get('country', [{}])[0].get('name', '')
            })
            seen.add(m.get('slug'))
        time.sleep(0.3)
    return results

def main():
    start_time = time.time()
    final_library = {
        "long_tieng": [],
        "thuyet_minh": [],
        "the_loai": {},
        "quoc_gia": {}
    }

    # 1. Quét Lồng Tiếng & Thuyết Minh (Kho 100 phim/loại)
    # Tăng limit riêng cho mục này vì ní muốn nó là "Thư viện"
    global LIMIT_PER_SECTION
    LIMIT_PER_SECTION = 100 
    final_library["long_tieng"] = crawl_by_filter('lang', 'long-tieng', 'Lồng Tiếng')
    final_library["thuyet_minh"] = crawl_by_filter('lang', 'thuyet-minh', 'Thuyết Minh')

    # 2. Quét Thể Loại (Kho 30 phim/loại)
    LIMIT_PER_SECTION = 30
    for cat in CATEGORIES:
        final_library["the_loai"][cat['slug']] = crawl_by_filter('the-loai', cat['slug'], cat['name'])

    # 3. Quét Quốc Gia (Kho 30 phim/loại)
    for cou in COUNTRIES:
        final_library["quoc_gia"][cou['slug']] = crawl_by_filter('quoc-gia', cou['slug'], cou['name'])

    # Lưu file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_library, f, ensure_ascii=False, indent=4)

    print(f"\n✅ ĐÃ XONG! Tổng thời gian: {int(time.time() - start_time)//60} phút.")

if __name__ == "__main__":
    main()
