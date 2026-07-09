import requests, json, os, time
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CẤU HÌNH ---
BASE_URL = "https://phimapi.com/v1/api"
YEARS_FILTER = [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017]
LIMIT_TOTAL = 300
MAX_WORKERS = 2 # Số luồng song song để lấy detail phim
OUTPUT_DIR = "data_categories"

if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

def get_data(url, params=None):
    try:
        res = requests.get(url, params=params, timeout=15)
        if res.status_code == 200: return res.json()
    except: pass
    return None

def fetch_detail(slug):
    # Lấy thông tin chi tiết của từng phim
    return get_data(f"{BASE_URL}/phim/{slug}")

def crawl_category(display_name, filename, country_slug, country_name, is_movie):
    results = []
    seen = set()
    page = 1
    
    print(f">>> Đang bào: {display_name}...")
    
    while len(results) < LIMIT_TOTAL:
        url = f"{BASE_URL}/quoc-gia/{country_slug}"
        data = get_data(url, {"page": page, "limit": 64})
        
        if not data or not data.get('data') or not data['data'].get('items'):
            break
            
        items = data['data']['items']
        slugs_to_fetch = []
        
        # Lọc nhanh các slug cần lấy detail
        for item in items:
            if item['slug'] in seen: continue
            
            # Lọc sơ bộ năm và loại phim ngay tại list để đỡ tốn request
            m_year = int(item.get('year', 0))
            is_single = (item.get('type') == 'single')
            
            if m_year in YEARS_FILTER and is_single == is_movie:
                slugs_to_fetch.append(item['slug'])
                seen.add(item['slug'])
        
        # Lấy thông tin chi tiết song song cho các phim hợp lệ
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_slug = {executor.submit(fetch_detail, slug): slug for slug in slugs_to_fetch}
            for future in as_completed(future_to_slug):
                d = future.result()
                if d and 'data' in d and 'item' in d['data']:
                    m = d['data']['item']
                    m_countries = m.get('country', [])
                    
                    results.append({
                        "name": m.get('name'), 
                        "year": m.get('year'), 
                        "slug": m.get('slug'), 
                        "thumb": m.get('thumb_url'), 
                        "poster": m.get('poster_url'), 
                        "sub_type": m.get('lang', 'Vietsub'), 
                        "current_episode": m.get('episode_current', 'Full'), 
                        "total_episodes": str(m.get('episode_total', '1')), 
                        "country": m_countries[0]['name'] if m_countries else country_name
                    })
                    if len(results) >= LIMIT_TOTAL: break
        
        print(f"    - Trang {page} | Thu thập: {len(results)}/{LIMIT_TOTAL}")
        page += 1
        time.sleep(0.5) 
        
    with open(os.path.join(OUTPUT_DIR, f"{filename}.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, separators=(',', ':'))
    
    return len(results)

if __name__ == "__main__":
    countries = [("viet-nam", "Việt Nam"), ("han-quoc", "Hàn Quốc"), ("trung-quoc", "Trung Quốc"), 
                 ("au-my", "Âu Mỹ"), ("thai-lan", "Thái Lan")]
    
    report = {}
    for c_slug, c_name in countries:
        c_key = c_slug.replace("-", "_")
        report[f"le_{c_key}.json"] = crawl_category(f"Lẻ {c_name}", f"le_{c_key}", c_slug, c_name, True)
        report[f"bo_{c_key}.json"] = crawl_category(f"Bộ {c_name}", f"bo_{c_key}", c_slug, c_name, False)
        
    print("\nHoàn tất:", report)
