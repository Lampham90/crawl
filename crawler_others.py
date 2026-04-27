import requests, json, time, os
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "https://phimapi.com/v1/api"
LIMIT_COUNT = 200
MAX_WORKERS = 2
OUTPUT_DIR = "data_categories"

if not os.path.exists(OUTPUT_DIR): 
    os.makedirs(OUTPUT_DIR)

def get_data(url, params=None):
    try:
        res = requests.get(url, params=params, timeout=15)
        return res.json() if res.status_code == 200 else None
    except: return None

def fetch_detail(slug):
    return get_data(f"https://phimapi.com/phim/{slug}")

def crawl_simple(display_name, filename, endpoint, category=None, lang=None):
    results, seen = [], set()
    
    # CHỖ NÀY QUAN TRỌNG: Chia rõ đường đi cho TV Show và các loại khác
    if endpoint == "tv-shows":
        # TV Show quét trực tiếp từ danh sách TV Show
        for page in range(1, 6): # Quét 5 trang để hốt cho đủ 200
            if len(results) >= LIMIT_COUNT: break
            url = f"{BASE_URL}/danh-sach/tv-shows"
            data = get_data(url, {"page": page, "limit": 64})
            
            if not data or 'data' not in data or not data['data'].get('items'): break
            
            items = data['data']['items']
            slugs = [it['slug'] for it in items if it['slug'] not in seen]
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                details = list(executor.map(fetch_detail, slugs))
                
            for d in details:
                if len(results) >= LIMIT_COUNT: break
                if not d or 'movie' not in d: continue
                m = d['movie']
                results.append({
                    "name": m.get('name'), "year": int(m.get('year', 0)), "slug": m.get('slug'), 
                    "thumb": m.get('thumb_url'), "poster": m.get('poster_url'), 
                    "sub_type": m.get('lang', 'Vietsub'), "current_episode": m.get('episode_current', 'Full'), 
                    "total_episodes": str(m.get('episode_total', '1')), "country": ""
                })
                seen.add(m.get('slug'))
    else:
        # Các mục khác vẫn quét theo năm 2026 -> 2023
        for year in [2026, 2025, 2024, 2023]:
            if len(results) >= LIMIT_COUNT: break
            url = f"{BASE_URL}/nam/{year}"
            params = {"page": 1, "limit": 64}
            if category: params['category'] = category
            if lang: params['sort_lang'] = lang
            
            data = get_data(url, params)
            if not data or 'data' not in data or not data['data'].get('items'): continue
            
            items = data['data']['items']
            slugs = [it['slug'] for it in items if it['slug'] not in seen]
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                details = list(executor.map(fetch_detail, slugs))
            
            for d in details:
                if len(results) >= LIMIT_COUNT: break
                if not d or 'movie' not in d: continue
                m = d['movie']
                results.append({
                    "name": m.get('name'), "year": int(m.get('year', 0)), "slug": m.get('slug'), 
                    "thumb": m.get('thumb_url'), "poster": m.get('poster_url'), 
                    "sub_type": m.get('lang', 'Vietsub'), "current_episode": m.get('episode_current', 'Full'), 
                    "total_episodes": str(m.get('episode_total', '1')), "country": ""
                })
                seen.add(m.get('slug'))
    
    with open(os.path.join(OUTPUT_DIR, f"{filename}.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, separators=(',', ':'))
    return len(results)

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
    
    print("\n" + "="*40 + "\n| BÁO CÁO THỂ LOẠI KHÁC |\n" + "-"*40)
    for k, v in report.items(): 
        print(f"| {k:22} | {v:11} |")
    print("="*40)
