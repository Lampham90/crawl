import requests, json, time, os
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "https://phimapi.com/v1/api"
YEARS = [2026, 2025, 2024, 2023]
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

def crawl_country_logic(display_name, filename, endpoint, country, is_movie):
    results, seen = [], set()
    print(f">>> Đang bào: {display_name}...")
    for year in YEARS:
        if len(results) >= LIMIT_COUNT: break
        for page in range(1, 15):
            if len(results) >= LIMIT_COUNT: break
            data = get_data(f"{BASE_URL}/danh-sach/{endpoint}", {"year": year, "page": page, "limit": 64})
            
            if not data or 'data' not in data or data['data'].get('items') is None: continue
            
            items = data['data']['items']
            slugs = [it['slug'] for it in items if it['slug'] not in seen]
            if not slugs: continue

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                details = list(executor.map(fetch_detail, slugs))
                
            for d in details:
                if len(results) >= LIMIT_COUNT: break
                if not d or 'movie' not in d: continue
                m = d['movie']
                
                # Loại trừ hoạt hình
                m_cats = [c.get('slug') for c in m.get('category', [])]
                if 'hoat-hinh' in m_cats: continue
                
                m_countries = [c.get('name') for c in m.get('country', [])]
                if country not in m_countries: continue
                
                results.append({
                    "name": m.get('name'), 
                    "year": int(m.get('year', 0)), 
                    "slug": m.get('slug'), 
                    "thumb": m.get('thumb_url'), 
                    "poster": m.get('poster_url'), 
                    "sub_type": "Vietsub", 
                    "current_episode": m.get('episode_current', 'Full'), 
                    "total_episodes": str(m.get('episode_total', '1')), 
                    "country": country
                })
                seen.add(m['slug'])
            time.sleep(0.1)

    with open(os.path.join(OUTPUT_DIR, f"{filename}.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, separators=(',', ':'))

if __name__ == "__main__":
    countries = [("Việt Nam", "viet"), ("Hàn Quốc", "han"), ("Trung Quốc", "trung"), ("Âu Mỹ", "au_my"), ("Thái Lan", "thai")]
    for c_name, c_key in countries:
        crawl_country_logic(f"Lẻ {c_name}", f"le_{c_key}", "phim-le", c_name, True)
        crawl_country_logic(f"Bộ {c_name}", f"bo_{c_key}", "phim-bo", c_name, False)
