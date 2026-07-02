import requests, json, os, time
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CẤU HÌNH (ĐÚNG CHUẨN CODE 1) ---
BASE_URL = "https://phimapi.com/v1/api"
YEARS = [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017]
LIMIT_COUNT = 300
MAX_WORKERS = 2  # Tăng lên 5 luồng để cào nhanh, không lo nghẽn
OUTPUT_DIR = "data_categories"

if not os.path.exists(OUTPUT_DIR): 
    os.makedirs(OUTPUT_DIR)

def get_data(url, params=None):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        res = requests.get(url, params=params, headers=headers, timeout=15)
        return res.json() if res.status_code == 200 else None
    except: 
        return None

def fetch_detail(slug):
    return get_data(f"{BASE_URL}/phim/{slug}")

def crawl_country_logic(display_name, filename, country_slug, country_filter, is_movie):
    results, seen = [], set()
    print(f">>> Đang bào: {display_name}...")
    
    all_slugs = []
    
    # Bước 1: Thu thập slug trực tiếp từ Endpoint Quốc gia (Giải quyết triệt để lỗi 3-4 phim)
    for year in YEARS:
        if len(all_slugs) >= LIMIT_COUNT * 2: 
            break
            
        for page in range(1, 20):  # Quét sâu trang của quốc gia đó
            if len(all_slugs) >= LIMIT_COUNT * 2: 
                break
                
            # Gọi thẳng API theo slug quốc gia (Vd: quoc-gia/viet-nam)
            url = f"{BASE_URL}/quoc-gia/{country_slug}"
            data = get_data(url, {"year": year, "page": page, "limit": 64})
            
            if not data or 'data' not in data or not data['data'].get('items'): 
                break
                
            items = data['data']['items']
            for it in items:
                slg = it['slug']
                if slg not in seen:
                    seen.add(slg)
                    all_slugs.append(slg)
                    
    print(f"    -> Tìm thấy {len(all_slugs)} phim sơ bộ. Đang tải chi tiết bằng ThreadPool...")
    
    # Bước 2: Dùng ThreadPool xử lý danh sách slug đã gom
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_slug = {executor.submit(fetch_detail, slug): slug for slug in all_slugs}
        
        for future in as_completed(future_to_slug):
            if len(results) >= LIMIT_COUNT: 
                break
                
            try:
                d = future.result()
                if not d or 'data' not in d or 'item' not in d['data']: 
                    continue
                    
                m = d['data']['item']
                
                # --- LOGIC LỌC SẠCH ---
                # 1. Loại bỏ Trailer
                ep_current = str(m.get('episode_current', '')).lower()
                if any(x in ep_current for x in ["trailer", "sắp ra mắt", "coming soon", "tập 0"]): 
                    continue
                
                # 2. Loại bỏ Hoạt hình
                if 'hoat-hinh' in [c.get('slug') for c in m.get('category', [])]: 
                    continue
                
                # 3. Phân loại chuẩn Phim Lẻ / Phim Bộ
                is_actually_movie = (m.get('type') == 'single' or str(m.get('episode_total')) == "1")
                if is_actually_movie != is_movie: 
                    continue
                
                # Thu thập data
                results.append({
                    "name": m.get('name'), 
                    "year": int(m.get('year', 0)), 
                    "slug": m.get('slug'), 
                    "thumb": m.get('thumb_url'), 
                    "poster": m.get('poster_url'), 
                    "sub_type": m.get('lang', 'Vietsub'), 
                    "current_episode": m.get('episode_current', 'Full'), 
                    "total_episodes": str(m.get('episode_total', '1')), 
                    "country": country_filter
                })
                
            except:
                continue
                
    # Lưu đúng file JSON riêng biệt theo cấu trúc cũ của bạn
    output_path = os.path.join(OUTPUT_DIR, f"{filename}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results[:LIMIT_COUNT], f, ensure_ascii=False, separators=(',', ':'))
        
    return len(results[:LIMIT_COUNT])

if __name__ == "__main__":
    report = {}
    
    # Cấu trúc: ("slug_api", "Tên quốc gia hiển thị", "Hậu tố file")
    countries = [
        ("viet-nam", "Việt Nam", "vn"), 
        ("han-quoc", "Hàn Quốc", "han"), 
        ("trung-quoc", "Trung Quốc", "trung"), 
        ("au-my", "Âu Mỹ", "au_my"), 
        ("thai-lan", "Thái Lan", "thai")
    ]
    
    for c_slug, c_name, c_key in countries:
        # Xuất file lẻ riêng (Ví dụ: le_vn.json)
        report[f"le_{c_key}.json"] = crawl_country_logic(f"Lẻ {c_name}", f"le_{c_key}", c_slug, c_name, True)
        # Xuất file bộ riêng (Ví dụ: bo_vn.json)
        report[f"bo_{c_key}.json"] = crawl_country_logic(f"Bộ {c_name}", f"bo_{c_key}", c_slug, c_name, False)
    
    print("\n" + "="*40 + "\n| BÁO CÁO PHIM QUỐC GIA CHUẨN |\n" + "-"*40)
    for k, v in report.items(): 
        print(f"| {k:22} | {v:11} |")
    print("="*40)
