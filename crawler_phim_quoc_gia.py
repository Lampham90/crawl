import requests, json, os, time
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "https://phimapi.com/v1/api"
YEARS_FILTER = [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017]
LIMIT_TOTAL = 300
OUTPUT_DIR = "data_categories"

if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

def get_data(url, params=None):
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200: return res.json()
    except: pass
    return None

def crawl_category(display_name, filename, country_slug, is_movie):
    results = []
    seen = set()
    page = 1
    
    print(f">>> Đang bào: {display_name}...")
    
    while len(results) < LIMIT_TOTAL:
        # Sử dụng endpoint QUỐC GIA - đây là nơi ổn định nhất của API này
        url = f"{BASE_URL}/quoc-gia/{country_slug}"
        data = get_data(url, {"page": page, "limit": 64})
        
        if not data or not data.get('data') or not data['data'].get('items'):
            break
            
        items = data['data']['items']
        
        for item in items:
            if len(results) >= LIMIT_TOTAL: break
            
            # Lọc sơ bộ bằng dữ liệu có sẵn trong item (không cần gọi fetch_detail ngay)
            # API trả về 'type': 'single' hoặc 'series'
            item_type = item.get('type')
            is_single = (item_type == 'single')
            
            if is_single != is_movie:
                continue
                
            m_year = int(item.get('year', 0))
            if m_year not in YEARS_FILTER:
                continue
                
            if item['slug'] not in seen:
                seen.add(item['slug'])
                results.append({
                    "name": item.get('name'),
                    "year": m_year,
                    "slug": item['slug'],
                    "thumb": item.get('thumb_url'),
                    "type": item_type
                })
        
        print(f"    - Trang {page} | Đã thu thập: {len(results)}")
        page += 1
        time.sleep(0.3) # Nghỉ để tránh bị chặn
        
    with open(os.path.join(OUTPUT_DIR, f"{filename}.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)
    return len(results)

# Chạy thử
countries = [("han-quoc", "han"), ("trung-quoc", "trung")] # Thử với Hàn và Trung trước
for c_slug, c_key in countries:
    crawl_category(f"Lẻ {c_key}", f"le_{c_key}", c_slug, True)
    crawl_category(f"Bộ {c_key}", f"bo_{c_key}", c_slug, False)
