import requests, json, os, time
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CẤU HÌNH ---
BASE_URL = "https://phimapi.com/v1/api"
YEARS_FILTER = [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017]
LIMIT_TOTAL = 300
MAX_WORKERS = 1
OUTPUT_DIR = "data_categories"

if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

def get_data(url, params=None):
    try:
        res = requests.get(url, params=params, timeout=15)
        if res.status_code == 200: return res.json()
    except: pass
    return None

def fetch_detail(slug):
    return get_data(f"{BASE_URL}/phim/{slug}")

def crawl_category(display_name, filename, country_slug, is_movie):
    results = []
    seen = set()
    page = 1
    
    while len(results) < LIMIT_TOTAL:
        url = f"{BASE_URL}/quoc-gia/{country_slug}"
        data = get_data(url, {"page": page, "limit": 64})
        
        if not data or not data.get('data') or not data['data'].get('items'): break
            
        items = data['data']['items']
        slugs_to_fetch = [it['slug'] for it in items if it['slug'] not in seen]
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_slug = {executor.submit(fetch_detail, s): s for s in slugs_to_fetch}
            for future in as_completed(future_to_slug):
                d = future.result()
                if d and 'data' in d and 'item' in d['data']:
                    m = d['data']['item']
                    m_year = int(m.get('year', 0))
                    # Kiểm tra logic phim lẻ / phim bộ
                    is_actually_movie = (m.get('type') == 'single' or str(m.get('episode_total')) == "1")
                    
                    if m_year in YEARS_FILTER and is_actually_movie == is_movie:
                        if m['slug'] not in seen:
                            seen.add(m['slug'])
                            results.append({
                                "name": m.get('name'), 
                                "year": m_year, 
                                "slug": m.get('slug'), 
                                "thumb": m.get('thumb_url'), 
                                "poster": m.get('poster_url'), 
                                "sub_type": m.get('lang', 'Vietsub'), 
                                "current_episode": m.get('episode_current', 'Full'), 
                                "total_episodes": str(m.get('episode_total', '1')), 
                                "country": country_slug
                            })
                    if len(results) >= LIMIT_TOTAL: break
        
        page += 1
        time.sleep(0.3)
        
    with open(os.path.join(OUTPUT_DIR, f"{filename}.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, separators=(',', ':'))
    
    return len(results)

if __name__ == "__main__":
    countries = [
        ("viet-nam", "vn"), ("han-quoc", "han"), ("trung-quoc", "trung"), 
        ("au-my", "au_my"), ("thai-lan", "thai")
    ]
    
    print(f"\n{'='*40}\n| BÁO CÁO CRAWL - {time.strftime('%d/%m')}\n{'-'*40}")
    
    for c_slug, c_key in countries:
        # Crawl Lẻ
        count_le = crawl_category(f"Lẻ {c_key}", f"le_{c_key}", c_slug, True)
        print(f"| Lẻ {c_key.replace('_', ' ').title():15} | {count_le:3} phim |")
        
        # Crawl Bộ
        count_bo = crawl_category(f"Bộ {c_key}", f"bo_{c_key}", c_slug, False)
        print(f"| Bộ {c_key.replace('_', ' ').title():15} | {count_bo:3} phim |")
        
    print(f"{'-'*40}")
