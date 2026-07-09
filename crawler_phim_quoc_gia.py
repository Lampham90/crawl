import requests, json, os, time
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CẤU HÌNH ---
BASE_URL = "https://phimapi.com/v1/api"
YEARS_FILTER = [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017]
LIMIT_TOTAL = 300
MAX_WORKERS = 2
OUTPUT_DIR = "data_categories"

if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

def get_data(url, params=None):
    try:
        res = requests.get(url, params=params, timeout=15)
        return res.json() if res.status_code == 200 else None
    except: return None

def crawl_category(display_name, filename, country_slug, is_movie):
    results = []
    seen = set()
    
    # Quét qua từng năm để đảm bảo không bỏ sót bất kỳ phim nào của năm đó
    for year in YEARS_FILTER:
        page = 1
        while True:
            # Dùng endpoint quoc-gia với filter năm
            url = f"{BASE_URL}/quoc-gia/{country_slug}"
            data = get_data(url, {"page": page, "limit": 64, "year": year})
            
            if not data or not data.get('data') or not data['data'].get('items'): break
            
            items = data['data']['items']
            for item in items:
                if item['slug'] in seen: continue
                
                # Fetch chi tiết để lọc Trailer & Kiểm tra type chuẩn xác
                d = get_data(f"{BASE_URL}/phim/{item['slug']}")
                if not d or 'data' not in d or 'item' not in d['data']: continue
                
                m = d['data']['item']
                ep_current = str(m.get('episode_current', '')).lower()
                
                # BỘ LỌC NGHIÊM NGẶT
                if any(x in ep_current for x in ["trailer", "sắp ra mắt", "coming soon", "tập 0"]): continue
                
                is_actually_movie = (m.get('type') == 'single' or str(m.get('episode_total')) == "1")
                if is_actually_movie != is_movie: continue
                
                seen.add(m['slug'])
                results.append({
                    "name": m.get('name'), "year": int(m.get('year', 0)), "slug": m.get('slug'),
                    "thumb": m.get('thumb_url'), "poster": m.get('poster_url'),
                    "sub_type": m.get('lang', 'Vietsub'), "current_episode": m.get('episode_current', 'Full'),
                    "total_episodes": str(m.get('episode_total', '1')), "country": country_slug
                })
            
            page += 1
            time.sleep(0.2)
            if len(results) >= LIMIT_TOTAL: break
        if len(results) >= LIMIT_TOTAL: break
    
    # SẮP XẾP THEO NĂM GIẢM DẦN
    results.sort(key=lambda x: x['year'], reverse=True)
    
    with open(os.path.join(OUTPUT_DIR, f"{filename}.json"), "w", encoding="utf-8") as f:
        json.dump(results[:LIMIT_TOTAL], f, ensure_ascii=False, separators=(',', ':'))
    
    return len(results)

# --- PHẦN BÁO CÁO GIỐNG ẢNH ---
if __name__ == "__main__":
    countries = [("viet-nam", "vn"), ("han-quoc", "han"), ("trung-quoc", "trung"), ("au-my", "au_my"), ("thai-lan", "thai")]
    print(f"\n{'='*40}\n| BÁO CÁO CRAWL - {time.strftime('%d/%m')}\n{'-'*40}")
    for c_slug, c_key in countries:
        c_name = c_key.replace("_", " ").title().replace("Au My", "Âu Mỹ").replace("Vn", "Việt Nam").replace("Han", "Hàn Quốc").replace("Trung", "Trung Quốc").replace("Thai", "Thái Lan")
        print(f"| Lẻ {c_name:15} | {crawl_category(f'Lẻ {c_key}', f'le_{c_key}', c_slug, True):3} phim |")
        print(f"| Bộ {c_name:15} | {crawl_category(f'Bộ {c_key}', f'bo_{c_key}', c_slug, False):3} phim |")
    print(f"{'-'*40}")
