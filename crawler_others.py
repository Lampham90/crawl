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
    
    # Duyệt qua các năm từ 2026 về 2023 để hốt đủ 400 phim
    for year in [2026, 2025, 2024, 2023]:
        if len(results) >= LIMIT_COUNT: break
        
        for page in range(1, 15):
            if len(results) >= LIMIT_COUNT: break
            
            # --- CHỌN LOGIC ENDPOINT ---
            if cat_slug is None:
                # Dành cho Lồng tiếng / Thuyết minh (Dùng endpoint Năm như code cũ của ní)
                url = f"{BASE_URL}/nam/{year}"
                params = {"page": page, "limit": 40, "sort_lang": lang}
            else:
                # Dành cho Thể loại (Dùng endpoint Thể loại hỗ trợ lọc Năm cực chuẩn)
                url = f"{BASE_URL}/the-loai/{cat_slug}"
                params = {"page": page, "limit": 40, "year": year, "sort_field": "modified.time", "sort_type": "desc"}

            data = get_data(url, params)
            if not data or 'data' not in data or not data['data'].get('items'): 
                break # Hết phim năm này, nhảy sang năm sau
                
            items = data['data']['items']
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
    # (Tên hiển thị, Tên file, Slug thể loại, Lang filter)
    # LƯU Ý: Lồng tiếng/Thuyết minh để Slug thể loại là None để dùng endpoint Năm.
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
    
    print("\n" + "="*45 + "\n| BÁO CÁO: KẾT HỢP CẢ 2 PHƯƠNG PHÁP |\n" + "-"*45)
    for k, v in report.items(): 
        print(f"| {k:22} | {v:14} |")
    print("="*45)
