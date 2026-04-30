import requests, json, time, os
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "https://phimapi.com/v1/api"
LIMIT_COUNT = 400
MAX_WORKERS = 4
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

def crawl_simple(display_name, filename, endpoint, category=None, lang=None):
    results, seen = [], set()
    print(f"\n>>> Đang bào {display_name}...")
    
    # Quét qua các năm từ 2026 lùi về để đảm bảo phim mới nhất
    for year in [2026, 2025, 2024, 2023, 2022]:
        if len(results) >= LIMIT_COUNT: break
        for page in range(1, 8): # Tăng lên 7 trang để vét kỹ hơn
            if len(results) >= LIMIT_COUNT: break
            
            url = f"{BASE_URL}/nam/{year}"
            params = {"page": page, "limit": 64}
            if category: params['category'] = category
            if lang: params['sort_lang'] = lang
            
            data = get_data(url, params)
            if not data or 'data' not in data or not data['data'].get('items'): break
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
        
        # --- LOGIC CHẶN TẬN GỐC DỰA TRÊN VÍ DỤ NÍ GỬI ---
        
        # 1. Lấy Type và ép kiểu về chuỗi thường để so sánh
        m_type = str(m.get('type', '')).lower().replace(" ", "")
        
        # 2. Lấy danh sách slug thể loại
        cat_slugs = [str(c.get('slug', '')).lower() for c in m.get('category', [])]
        
        # 3. Kiểm tra từ khóa trong tên phim và nội dung ngắn (nếu cần)
        m_name = m.get('name', '').lower()

        # ĐIỀU KIỆN LOẠI BỎ (Chỉ cần dính 1 trong các dấu hiệu này)
        is_animation = (
            "hoathinh" in m_type or             # Chặn đúng ví dụ ní gửi
            "hoat-hinh" in m_type or            # Chặn biến thể có gạch
            "hoat-hinh" in cat_slugs or         # Chặn theo tag thể loại
            "anime" in cat_slugs or             # Chặn Anime
            "hoạt hình" in m_name or            # Chặn theo tên phim
            "hoat hinh" in m_name               # Chặn tên không dấu
        )
        
        if is_animation:
            continue 
        # ----------------------------------------------

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
        ("Lồng Tiếng", "long_tieng", "phim-moi", None, "long-tieng"), 
        ("Thuyết Minh", "thuyet_minh", "phim-moi", None, "thuyet-minh"),
        ("Kinh Dị", "kinh_di", "phim-moi", "kinh-di", None), 
        ("Hài Hước", "hai_huoc", "phim-moi", "hai-huoc", None),
        ("Cổ Trang", "co_trang", "phim-moi", "co-trang", None), 
        ("Khoa Học", "khoa_hoc", "phim-moi", "khoa-hoc", None),
        ("Hành Động", "hanh_dong", "phim-moi", "hanh-dong", None)
    ]
    
    for d_name, f_name, endp, cat, lng in targets:
        report[f"{f_name}.json"] = crawl_simple(d_name, f_name, endp, cat, lng)
    
    print("\n" + "="*45 + "\n| BÁO CÁO CÀO DỮ LIỆU: SẠCH 100% |\n" + "-"*45)
    for k, v in report.items(): 
        print(f"| {k:22} | {v:14} |")
    print("="*45)
