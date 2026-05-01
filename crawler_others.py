import requests, json, time, os
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "https://phimapi.com/v1/api"
LIMIT_COUNT = 400
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
    return get_data(f"{BASE_URL}/phim/{slug}")

def crawl_universal(display_name, filename, cat_slug=None, lang=None):
    results, seen = [], set()
    print(f"\n>>> Đang bào {display_name}...")
    
    # Mở rộng danh sách năm để đảm bảo đủ 400 phim (về tận 2020 nếu cần)
    years_to_check = [2026, 2025, 2024, 2023, 2022, 2021, 2020]
    
    for year in years_to_check:
        if len(results) >= LIMIT_COUNT: break
        print(f"  + Quét năm {year}...")
        
        # Tăng số trang quét lên (ví dụ 30 trang) để không sót phim Lồng tiếng nào
        for page in range(1, 31): 
            if len(results) >= LIMIT_COUNT: break
            
            if cat_slug is None:
                # Dành cho Lồng tiếng / Thuyết minh
                url = f"{BASE_URL}/nam/{year}"
                params = {"page": page, "limit": 40, "sort_lang": lang}
            else:
                # Dành cho Thể loại
                url = f"{BASE_URL}/the-loai/{cat_slug}"
                params = {"page": page, "limit": 40, "year": year, "sort_field": "modified.time", "sort_type": "desc"}

            data = get_data(url, params)
            # Nếu data rỗng hoặc không có items thì dừng trang của năm đó
            if not data or 'data' not in data or not data['data'].get('items'):
                break
                
            items = data['data']['items']
            if not items: break
            
            process_and_add(items, results, seen)
                
    with open(os.path.join(OUTPUT_DIR, f"{filename}.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, separators=(',', ':'))
    return len(results)

def process_and_add(items, results, seen):
    slugs = [it['slug'] for it in items if it['slug'] not in seen]
    if not slugs: return

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        details = list(executor.map(fetch_detail, slugs))
    
    for d in details:
        if len(results) >= LIMIT_COUNT: break
        if not d or 'data' not in d or 'item' not in d['data']: continue
        m = d['data']['item']
        
        # --- BỘ LỌC HOẠT HÌNH ---
        m_type = str(m.get('type', '')).lower().replace(" ", "")
        cat_slugs = [str(c.get('slug', '')).lower() for c in m.get('category', [])]
        m_name = m.get('name', '').lower()

        if any(x in m_type for x in ['hoathinh', 'hoat-hinh']) or \
           any(x in cat_slugs for x in ['hoat-hinh', 'anime']) or \
           "hoạt hình" in m_name or "hoat hinh" in m_name:
            continue 

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

if __name__ == "__main__":
    report = {}
    targets = [
        ("Lồng Tiếng", "long_tieng", None, "long-tieng"), 
        ("Thuyết Minh", "thuyet_minh", None, "thuyet-minh"),
        ("Kinh Dị", "kinh_di", "kinh-di", None), 
        ("Hài Hước", "hai_huoc", "hai-huoc", None),
        ("Cổ Trang", "co_trang", "co-trang", None), 
        ("Khoa Học", "khoa_hoc", "khoa-hoc", None),
        ("Hành Động", "hanh_dong", "hanh-dong", None)
    ]
    
    for d_name, f_name, cat, lng in targets:
        report[f"{f_name}.json"] = crawl_universal(d_name, f_name, cat, lng)
    
    print("\n" + "="*45 + "\n| BÁO CÁO: TỐI ƯU SỐ LƯỢNG PHIM |\n" + "-"*45)
    for k, v in report.items(): 
        print(f"| {k:22} | {v:14} |")
    print("="*45)
