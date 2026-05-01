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
    
    # Ưu tiên quét 2026 trước
    years_to_check = [2026, 2025, 2024, 2023]
    
    for year in years_to_check:
        if len(results) >= LIMIT_COUNT: break
        
        # Quay lại dùng endpoint danh-sach/phim-le hoặc phim-bo sẽ ổn định filter hơn
        # Hoặc dùng trực tiếp danh-sach/phim-moi để lấy đa dạng
        for page in range(1, 11): 
            if len(results) >= LIMIT_COUNT: break
            
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
            
            # Xử lý chi tiết
            process_and_add(data['data']['items'], results, seen)
                
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
        
        # --- LOGIC CHẶN HOẠT HÌNH CỰC GẮT ---
        m_type = str(m.get('type', '')).lower().replace(" ", "")
        cat_slugs = [str(c.get('slug', '')).lower() for c in m.get('category', [])]
        m_name = m.get('name', '').lower()

        # Nếu có dấu hiệu hoạt hình thì skip
        if any(x in m_type for x in ['hoathinh', 'hoat-hinh']) or \
           any(x in cat_slugs for x in ['hoat-hinh', 'anime']) or \
           "hoạt hình" in m_name:
            continue 
        
        # Lưu dữ liệu
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
        report[f"{f_name}.json"] = crawl_simple(d_name, f_name, cat, lng)
    
    print("\n" + "="*45 + "\n| BÁO CÁO: ĐÃ FIX LỖI 0 PHIM |\n" + "-"*45)
    for k, v in report.items(): 
        print(f"| {k:22} | {v:14} |")
    print("="*45)
