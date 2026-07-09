import requests, json, os, time
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CẤU HÌNH ---
BASE_URL = "https://phimapi.com/v1/api"
YEARS_FILTER = [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017]
LIMIT_TOTAL = 300
MAX_WORKERS = 3
OUTPUT_DIR = "data_categories"

if not os.path.exists(OUTPUT_DIR): 
    os.makedirs(OUTPUT_DIR)

def get_data(url, params=None):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        res = requests.get(url, params=params, headers=headers, timeout=15)
        if res.status_code == 200:
            return res.json()
    except: pass
    return None

def fetch_detail(slug):
    time.sleep(0.1) 
    return get_data(f"{BASE_URL}/phim/{slug}")

def crawl_category(display_name, filename, country_slug, is_movie):
    results = []
    seen = set()
    
    # Endpoint xác định loại phim
    type_endpoint = "phim-le" if is_movie else "phim-bo"
    url = f"{BASE_URL}/danh-sach/{type_endpoint}"
    
    print(f">>> Đang bào: {display_name}...")
    
    for year in YEARS_FILTER:
        if len(results) >= LIMIT_TOTAL: break
        
        page = 1
        while True:
            params = {"page": page, "limit": 64, "country": country_slug, "year": year}
            data = get_data(url, params=params)
            
            if not data or not data.get('data') or not data['data'].get('items'):
                break
                
            items = data['data']['items']
            slugs = [it['slug'] for it in items if it['slug'] not in seen]
            
            if not slugs: break
            
            # Xử lý chi tiết từng phim
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                future_to_slug = {executor.submit(fetch_detail, s): s for s in slugs}
                for future in as_completed(future_to_slug):
                    d = future.result()
                    if d and 'data' in d and 'item' in d['data']:
                        m = d['data']['item']
                        if m['slug'] not in seen:
                            seen.add(m['slug'])
                            results.append({
                                "name": m.get('name'), "year": m.get('year'), "slug": m.get('slug'),
                                "thumb": m.get('thumb_url'), "poster": m.get('poster_url'),
                                "sub_type": m.get('lang', 'Vietsub'), "current_episode": m.get('episode_current', 'Full'),
                                "total_episodes": str(m.get('episode_total', '1'))
                            })
            
            print(f"    - Năm {year} | Trang {page} | Đã gom: {len(results)}")
            if len(results) >= LIMIT_TOTAL: break
            page += 1
            time.sleep(0.2)

    # Lưu file
    final_results = results[:LIMIT_TOTAL]
    with open(os.path.join(OUTPUT_DIR, f"{filename}.json"), "w", encoding="utf-8") as f:
        json.dump(final_results, f, ensure_ascii=False, separators=(',', ':'))
    return len(final_results)

if __name__ == "__main__":
    countries = [("viet-nam", "vn"), ("han-quoc", "han"), ("trung-quoc", "trung"), ("au-my", "au_my"), ("thai-lan", "thai")]
    report = {}
    
    for c_slug, c_key in countries:
        report[f"le_{c_key}.json"] = crawl_category(f"Lẻ {c_key.upper()}", f"le_{c_key}", c_slug, True)
        report[f"bo_{c_key}.json"] = crawl_category(f"Bộ {c_key.upper()}", f"bo_{c_key}", c_slug, False)
        
    print("\nHoàn tất. Báo cáo:", report)
