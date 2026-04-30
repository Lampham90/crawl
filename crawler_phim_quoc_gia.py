import requests, json, time, os
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "https://phimapi.com/v1/api"
YEARS = [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017]
LIMIT_COUNT = 300
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
    for year in YEARS:
        if len(results) >= LIMIT_COUNT: break
        for page in range(1, 15):
            if len(results) >= LIMIT_COUNT: break
            data = get_data(f"{BASE_URL}/danh-sach/{endpoint}", {"year": year, "page": page, "limit": 64})
            if not data or 'data' not in data or data['data'].get('items') is None: continue
            slugs = [it['slug'] for it in data['data']['items'] if it['slug'] not in seen]
            if not slugs: continue
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                details = list(executor.map(fetch_detail, slugs))
            for d in details:
                if len(results) >= LIMIT_COUNT: break
                if not d or 'movie' not in d: continue
                m = d['movie']
                if 'hoat-hinh' in [c.get('slug') for c in m.get('category', [])]: continue
                if country not in [c.get('name') for c in m.get('country', [])]: continue
                results.append({
                    "name": m.get('name'), "year": int(m.get('year', 0)), "slug": m.get('slug'), 
                    "thumb": m.get('thumb_url'), "poster": m.get('poster_url'), 
                    "sub_type": m.get('lang', 'Vietsub'), "current_episode": m.get('episode_current', 'Full'), 
                    "total_episodes": str(m.get('episode_total', '1')), "country": country
                })
                seen.add(m['slug'])
    with open(os.path.join(OUTPUT_DIR, f"{filename}.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, separators=(',', ':'))
    return len(results)

if __name__ == "__main__":
    report = {}
    countries = [("Việt Nam", "viet"), ("Hàn Quốc", "han"), ("Trung Quốc", "trung"), ("Âu Mỹ", "au_my"), ("Thái Lan", "thai")]
    for c_name, c_key in countries:
        report[f"le_{c_key}.json"] = crawl_country_logic(f"Lẻ {c_name}", f"le_{c_key}", "phim-le", c_name, True)
        report[f"bo_{c_key}.json"] = crawl_country_logic(f"Bộ {c_name}", f"bo_{c_key}", "phim-bo", c_name, False)
    
    print("\n" + "="*35 + "\n| BÁO CÁO PHIM QUỐC GIA |\n" + "-"*35)
    for k, v in report.items(): print(f"| {k:20} | {v:7} |")
    print("="*35)
