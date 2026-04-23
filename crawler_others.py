import requests, json, time, os
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "https://phimapi.com/v1/api"
LIMIT_COUNT = 200
MAX_WORKERS = 2
OUTPUT_DIR = "data_categories"

def get_data(url, params=None):
    try:
        res = requests.get(url, params=params, timeout=15)
        return res.json() if res.status_code == 200 else None
    except: return None

def fetch_detail(slug):
    return get_data(f"https://phimapi.com/phim/{slug}")

def crawl_simple(display_name, filename, endpoint, category=None, lang=None):
    results, seen = [], set()
    print(f">>> Đang bào: {display_name}...")
    for year in [2026, 2025, 2024, 2023]:
        if len(results) >= LIMIT_COUNT: break
        params = {"page": 1, "limit": 64}
        if category: params['category'] = category
        if lang: params['sort_lang'] = lang
        
        data = get_data(f"{BASE_URL}/nam/{year}", params)
        if not data or 'data' not in data or data['data'].get('items') is None: continue
        
        items = data['data']['items']
        slugs = [it['slug'] for it in items if it['slug'] not in seen]
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            details = list(executor.map(fetch_detail, slugs))
            
        for d in details:
            if len(results) >= LIMIT_COUNT: break
            if not d or 'movie' not in d: continue
            m = d['movie']
            
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
            
    with open(os.path.join(OUTPUT_DIR, f"{filename}.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, separators=(',', ':'))

if __name__ == "__main__":
    crawl_simple("Lồng Tiếng", "long_tieng", "phim-moi", lang="long-tieng")
    crawl_simple("Thuyết Minh", "thuyet_minh", "phim-moi", lang="thuyet-minh")
    crawl_simple("Kinh Dị", "kinh_di", "phim-moi", category="kinh-di")
    crawl_simple("Hài", "hai_huoc", "phim-moi", category="hai-huoc")
    crawl_simple("Cổ Trang", "co_trang", "phim-moi", category="co-trang")
    crawl_simple("Khoa Học", "khoa_hoc", "phim-moi", category="khoa-hoc")
    crawl_simple("TV Show", "tv_show", "tv-shows")
