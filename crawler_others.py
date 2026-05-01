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

def crawl_master(display_name, filename, category_slug="phim-moi", lang="", year_filter=2026):
    results, seen = [], set()
    print(f"\n>>> Đang bào {display_name} năm {year_filter}...")
    
    # Ép API sắp xếp theo thời gian cập nhật mới nhất (modified.time) và giảm dần (desc)
    # Nếu category_slug là None, ta mặc định dùng danh mục chung 'phim-moi'
    endpoint = f"the-loai/{category_slug}" if category_slug else "danh-sach/phim-moi"
    
    for page in range(1, 15): # Quét sâu để lấy đủ 400 phim nếu có
        if len(results) >= LIMIT_COUNT: break
        
        params = {
            "page": page,
            "limit": 40,
            "sort_field": "modified.time", # Sắp xếp theo ngày cập nhật
            "sort_type": "desc",           # Mới nhất lên đầu
            "sort_lang": lang,             # Lọc lồng tiếng / thuyết minh
            "year": year_filter            # Lọc đúng năm ní muốn
        }
        
        data = get_data(f"{BASE_URL}/{endpoint}", params)
        if not data or 'data' not in data or not data['data'].get('items'):
            break
            
        items = data['data']['items']
        process_and_add(items, results, seen)
                
    # Sau khi cào xong, ghi ra file
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
        
        # --- BỘ LỌC HOẠT HÌNH TRIỆT ĐỂ ---
        m_type = str(m.get('type', '')).lower().replace(" ", "")
        cat_slugs = [str(c.get('slug', '')).lower() for c in m.get('category', [])]
        m_name = m.get('name', '').lower()

        if any(x in m_type for x in ['hoathinh', 'hoat-hinh']) or \
           any(x in cat_slugs for x in ['hoat-hinh', 'anime']) or \
           "hoạt hình" in m_name or "hoat hinh" in m_name:
            continue 
        # ---------------------------------

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
    # Ní muốn 2026 thì tui set mặc định 2026. Nếu muốn cào thêm 2025 thì chạy thêm vòng lặp.
    CURRENT_YEAR = 2026
    
    # (Tên hiển thị, Tên file, Slug thể loại, Filter ngôn ngữ)
    targets = [
        ("Lồng Tiếng", "long_tieng", None, "long-tieng"), 
        ("Thuyết Minh", "thuyet_minh", None, "thuyet-minh"),
        ("Kinh Dị", "kinh_di", "kinh-di", ""), 
        ("Hài Hước", "hai_huoc", "hai-huoc", ""),
        ("Cổ Trang", "co_trang", "co-trang", ""), 
        ("Khoa Học", "khoa_hoc", "khoa-hoc", ""),
        ("Hành Động", "hanh_dong", "hanh-dong", "")
    ]
    
    for d_name, f_name, cat_slug, lng in targets:
        # Cào cho năm 2026
        count = crawl_master(d_name, f_name, cat_slug, lng, year_filter=CURRENT_YEAR)
        report[f"{f_name}.json"] = count
    
    print("\n" + "="*45 + "\n| BÁO CÁO: ĐÃ FIX THEO URL VÍ DỤ |\n" + "-"*45)
    for k, v in report.items(): 
        print(f"| {k:22} | {v:14} |")
    print("="*45)
