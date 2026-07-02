import requests, json, os, time
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CẤU HÌNH ---
BASE_URL = "https://phimapi.com/v1/api"
YEARS = [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017]
LIMIT_COUNT = 300
MAX_WORKERS = 3  # Tăng lên 5 để tối ưu tốc độ ThreadPool hiệu quả hơn
OUTPUT_DIR = "data_categories"

if not os.path.exists(OUTPUT_DIR): 
    os.makedirs(OUTPUT_DIR)

def get_data(url, params=None):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        res = requests.get(url, params=params, headers=headers, timeout=10)
        return res.json() if res.status_code == 200 else None
    except: 
        return None

def fetch_detail(slug):
    return get_data(f"{BASE_URL}/phim/{slug}")

def crawl_country_logic(display_name, filename, endpoint, country_filter, is_movie):
    results, seen = [], set()
    print(f">>> Đang bào: {display_name}...")
    
    # Bước 1: Thu thập tất cả các slug hợp lệ từ các trang trước để tránh gọi bừa bãi
    all_slugs = []
    
    for year in YEARS:
        if len(all_slugs) >= LIMIT_COUNT * 2: # Lấy dư slug để trừ hao lúc lọc detail
            break
            
        for page in range(1, 16):
            if len(all_slugs) >= LIMIT_COUNT * 2: 
                break
                
            data = get_data(f"{BASE_URL}/danh-sach/{endpoint}", {"year": year, "page": page, "limit": 64})
            if not data or 'data' not in data or not data['data'].get('items'): 
                break
                
            items = data['data']['items']
            for it in items:
                slg = it['slug']
                if slg not in seen:
                    seen.add(slg)
                    all_slugs.append(slg)
                    
    # Bước 2: Dùng ThreadPoolExecutor tập trung ở ngoài để cào chi tiết hàng loạt
    print(f"    -> Tìm thấy {len(all_slugs)} phim sơ bộ. Đang tải chi tiết...")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Gửi toàn bộ request đi cùng một lúc
        future_to_slug = {executor.submit(fetch_detail, slug): slug for slug in all_slugs}
        
        for future in as_completed(future_to_slug):
            if len(results) >= LIMIT_COUNT: 
                break
                
            try:
                d = future.result()
                if not d or 'data' not in d or 'item' not in d['data']: 
                    continue
                    
                m = d['data']['item']
                
                # --- LOGIC LỌC ---
                # 1. Loại bỏ Trailer / Sắp ra mắt
                ep_current = str(m.get('episode_current', '')).lower()
                if any(x in ep_current for x in ["trailer", "sắp ra mắt", "coming soon"]): 
                    continue
                
                # 2. Loại bỏ hoạt hình
                if 'hoat-hinh' in [c.get('slug') for c in m.get('category', [])]: 
                    continue
                    
                # 3. Lọc chuẩn Quốc gia
                if country_filter not in [c.get('name') for c in m.get('country', [])]: 
                    continue
                
                # 4. Phân loại Phim Lẻ / Phim Bộ
                is_actually_movie = (m.get('type') == 'single' or str(m.get('episode_total')) == "1")
                if is_actually_movie != is_movie: 
                    continue
                
                # Lưu kết quả hợp lệ
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
                
            except Exception as e:
                # Bỏ qua nếu luồng này lỗi kết nối ngầm
                continue
                
    # Lưu file JSON sau khi đã thu thập đủ/hết danh sách
    output_path = os.path.join(OUTPUT_DIR, f"{filename}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results[:LIMIT_COUNT], f, ensure_ascii=False, separators=(',', ':'))
        
    return len(results[:LIMIT_COUNT])

if __name__ == "__main__":
    report = {}
    countries = [
        ("Việt Nam", "vn"), 
        ("Hàn Quốc", "han"), 
        ("Trung Quốc", "trung"), 
        ("Âu Mỹ", "au_my"), 
        ("Thái Lan", "thai")
    ]
    
    for c_name, c_key in countries:
        report[f"le_{c_key}.json"] = crawl_country_logic(f"Lẻ {c_name}", f"le_{c_key}", "phim-le", c_name, True)
        report[f"bo_{c_key}.json"] = crawl_country_logic(f"Bộ {c_name}", f"bo_{c_key}", "phim-bo", c_name, False)
    
    print("\n" + "="*40 + "\n| BÁO CÁO PHIM QUỐC GIA CHUẨN |\n" + "-"*40)
    for k, v in report.items(): 
        print(f"| {k:22} | {v:11} |")
    print("="*40)
