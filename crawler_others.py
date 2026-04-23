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

def crawl_simple(display_name, filename, endpoint, category=None, lang=None):
    results, seen = [], set()
    print(f">>> Đang bào: {display_name}...")
    for year in [2026, 2025, 2024, 2023]:
        if len(results) >= LIMIT_COUNT: break
        params = {"page": 1, "limit": 64}
        if category: params['category'] = category
        if lang: params['sort_lang'] = lang
        data = get_data(f"{BASE_URL}/nam/{year}", params)
        if not data: continue
        for m in data['data']['items']:
            if len(results) >= LIMIT_COUNT: break
            results.append({"name": m.get('name'), "year": year, "slug": m.get('slug'), "thumb": m.get('thumb_url'), "poster": m.get('poster_url'), "sub_type": display_name if lang else "Vietsub", "current_episode": m.get('episode_current', 'Full'), "total_episodes": "1", "country": ""})
            seen.add(m['slug'])
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
