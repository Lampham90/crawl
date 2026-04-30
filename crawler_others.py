import requests, json, time, os
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "https://phimapi.com/v1/api"
LIMIT_COUNT = 400
MAX_WORKERS = 10 
OUTPUT_DIR = "data_categories"

if not os.path.exists(OUTPUT_DIR): 
    os.makedirs(OUTPUT_DIR)

def get_data(url, params=None):
    try:
        res = requests.get(url, params=params, timeout=15)
        return res.json() if res.status_code == 200 else None
    except: return None

def fetch_detail(slug):
    return get_data(f"{BASE_URL}/phim/{slug}")

def crawl_simple(display_name, filename, endpoint, category=None, lang=None):
    results, seen = [], set()
    print(f"\n>>> Đang bào {display_name}...")
    
    if endpoint == "tv-shows":
        for page in range(1, 11):
            if len(results) >= LIMIT_COUNT: break
            url = f"{BASE_URL}/danh-sach/tv-shows"
            data = get_data(url, {"page": page, "limit": 64})
            if not data or 'data' not in data or not data['data'].get('items'): break
            items = data['data']['items']
            process_and_add(items, results, seen)
    else:
        for year in [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015]:
            if len(results) >= LIMIT_COUNT: break
            for page in range(1, 4):
                if len(results) >= LIMIT_COUNT: break
                url = f"{BASE_URL}/nam/{year}"
                params = {"page": page, "limit": 64}
                if category: params['category'] = category
                if lang: params['sort_lang'] = lang
                data = get_data(url, params)
                if not data or 'data' not in data or not data['data'].get('items'): break
                items = data['data']['items']
                process_and_add(items, results, seen)
                
    with open(os.path.join(OUTPUT_DIR, f"{filename}.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, separators=(',', ':'))
    return len(results)

def process_and_add(items, results, seen):
    slugs = [it['slug'] for it in items if it['slug'] not in seen]
    if not slugs: return

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        details = list(executor.map(fetch_detail, slugs))
    
    for d in details:
        if len(results) >= LIMIT_COUNT: break
        if not d or 'data' not in d or 'item' not in d['data']: continue
        m = d['data']['item']
        
        # --- ĐIỀU KIỆN LOẠI TRỪ HOẠT HÌNH ---
        # Lấy danh sách slug của tất cả thể loại phim này thuộc về
        movie_cats = [c.get('slug') for c in m.get('category', [])]
        if 'hoat-hinh' in movie_cats: 
            continue # Nếu là hoạt hình thì bỏ qua, không thêm vào list
        # ------------------------------------

        results.append({
            "name": m.get('name'), 
            "year": int(m.get('year', 0)), 
            "slug": m.get('slug'), 
            "thumb": m.get('thumb_url'), 
            "poster": m.get('poster_url'), 
            "sub_type": m.get('lang', 'Vietsub'), 
            "current_episode": m.get('episode_current', 'Full'), 
            "total_episodes": str(m.get('episode_total', '1')), 
            "country": ""
        })
        seen.add(m.get('slug'))

if __name__ == "__main__":
    report = {}
    targets = [
        ("Lồng Tiếng", "long_tieng", "phim-moi", None, "long-tieng"), 
        ("Thuyết Minh", "thuyet_minh", "phim-moi", None, "thuyet-minh"),
        ("Kinh Dị", "kinh_di", "phim-moi", "kinh-di", None), 
        ("Hài", "hai_huoc", "phim-moi", "hai-huoc", None),
        ("Cổ Trang", "co_trang", "phim-moi", "co-trang", None), 
        ("Khoa Học", "khoa_hoc", "phim-moi", "khoa-hoc", None),
        ("TV Show", "tv_show", "tv-shows", None, None)
    ]
    
    for d_name, f_name, endp, cat, lng in targets:
        report[f"{f_name}.json"] = crawl_simple(d_name, f_name, endp, cat, lng)
    
    print("\n" + "="*45 + "\n| BÁO CÁO CÀO DỮ LIỆU HOÀN TẤT |\n" + "-"*45)
    for k, v in report.items(): 
        print(f"| {k:22} | {v:14} |")
    print("="*45)
