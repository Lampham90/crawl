import requests, json, time, os
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "https://phimapi.com/v1/api"
LIMIT_COUNT = 400
MAX_WORKERS = 3
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

def crawl_simple(display_name, filename, category_slug=None, lang_filter=None):
    results, seen = [], set()
    print(f"\n>>> Đang bào {display_name}...")
    
    # Danh sách năm cần quét
    years_to_check = [2026, 2025, 2024, 2023]
    
    for year in years_to_check:
        if len(results) >= LIMIT_COUNT: break
        
        # Dùng endpoint danh-sach để filter chuẩn hơn
        # Nếu là thể loại, ta dùng endpoint 'phim-moi' hoặc 'danh-sach' kèm params
        for page in range(1, 11): 
            if len(results) >= LIMIT_COUNT: break
            
            # Tối ưu: Gọi endpoint danh sách phim mới nhất kèm filter năm và thể loại
            url = f"{BASE_URL}/danh-sach/phim-moi"
            params = {
                "page": page, 
                "limit": 64,
                "year": year
            }
            if category_slug: params['category'] = category_slug
            if lang_filter: params['sort_lang'] = lang_filter
            
            data = get_data(url, params)
            if not data or 'data' not in data or not data['data'].get('items'): break
            
            # Xử lý chi tiết để lọc hoạt hình
            process_and_add(data['data']['items'], results, seen, year)
                
    with open(os.path.join(OUTPUT_DIR, f"{filename}.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, separators=(',', ':'))
    return len(results)

def process_and_add(items, results, seen, target_year):
    slugs = [it['slug'] for it in items if it['slug'] not in seen]
    if not slugs: return

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        details = list(executor.map(fetch_detail, slugs))
    
    for d in details:
        if len(results) >= LIMIT_COUNT: break
        if not d or 'data' not in d or 'item' not in d['data']: continue
        m = d['data']['item']
        
        # --- LỌC HOẠT HÌNH ---
        m_type = str(m.get('type', '')).lower().replace(" ", "")
        cat_slugs = [str(c.get('slug', '')).lower() for c in m.get('category', [])]
        m_name = m.get('name', '').lower()

        if any(x in m_type for x in ['hoathinh', 'hoat-hinh']) or \
           any(x in cat_slugs for x in ['hoat-hinh', 'anime']) or \
           "hoạt hình" in m_name:
            continue 
        
        # --- LỌC CHUẨN NĂM (Phòng hờ API trả về sai năm) ---
        if int(m.get('year', 0)) != target_year:
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
    # Định nghĩa lại các mục tiêu: (Tên hiển thị, Tên file, Category Slug, Lang Filter)
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
        report[f"{f_name}.json"] = crawl_simple(d_name, f_name, cat, lng)
    
    print("\n" + "="*45 + "\n| BÁO CÁO: QUÉT SẠCH PHIM 2026 |\n" + "-"*45)
    for k, v in report.items(): 
        print(f"| {k:22} | {v:14} |")
    print("="*45)
