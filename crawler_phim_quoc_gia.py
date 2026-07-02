import requests, json, os, time
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CẤU HÌNH ---
BASE_URL = "https://phimapi.com/v1/api"
# Giữ YEARS_FILTER để lọc trong bước check chi tiết phim
YEARS_FILTER = [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017]
LIMIT_COUNT = 300
MAX_WORKERS = 2  # Giảm xuống 4 luồng để tránh bị API chặn IP ngầm
OUTPUT_DIR = "data_categories"

if not os.path.exists(OUTPUT_DIR): 
    os.makedirs(OUTPUT_DIR)

def get_data(url, params=None):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        res = requests.get(url, params=params, headers=headers, timeout=15)
        if res.status_code == 200:
            return res.json()
    except: 
        pass
    return None

def fetch_detail(slug):
    # Nghỉ cực ngắn để tránh bị nghẽn API chi tiết
    time.sleep(0.1)
    return get_data(f"{BASE_URL}/phim/{slug}")

def crawl_country_logic(display_name, filename, country_slug, country_filter, is_movie):
    results = []
    seen = set()  # Đảm bảo độc lập hoàn toàn giữa các lần gọi hàm
    all_slugs = []
    
    print(f">>> Đang bào: {display_name}...")
    
    page = 1
    total_pages = 1
    
    # Bước 1: Quét tuần tự các trang của quốc gia đó (Không lặp lồng theo năm nữa)
    while page <= total_pages:
        # Nếu đã gom đủ lượng slug cần thiết thì dừng quét trang sơ bộ
        if len(all_slugs) >= LIMIT_COUNT * 3:
            break
            
        url = f"{BASE_URL}/quoc-gia/{country_slug}"
        data = get_data(url, {"page": page, "limit": 64})
        
        if not data or 'data' not in data or not data['data'].get('items'): 
            break
            
        # Cập nhật tổng số trang từ API trả về để chạy vòng lặp chuẩn
        total_pages = int(data['data'].get('params', {}).get('pagination', {}).get('totalPages', 1))
        
        items = data['data']['items']
        for it in items:
            slg = it['slug']
            if slg not in seen:
                seen.add(slg)
                all_slugs.append(slg)
                
        page += 1
        time.sleep(0.2) # Nghỉ chút để API không block
        
    print(f"    -> Tìm thấy {len(all_slugs)} phim sơ bộ. Đang tải chi tiết bằng ThreadPool...")
    if not all_slugs:
        return 0
        
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
                
                # --- LOGIC LỌC ---
                # 1. Lọc năm phát hành (Vì bước trước không lọc được bằng API)
                if int(m.get('year', 0)) not in YEARS_FILTER:
                    continue
                
                # 2. Loại bỏ Trailer / Sắp ra mắt
                ep_current = str(m.get('episode_current', '')).lower()
                if any(x in ep_current for x in ["trailer", "sắp ra mắt", "coming soon", "tập 0"]): 
                    continue
                
                # 3. Loại bỏ Hoạt hình
                if 'hoat-hinh' in [c.get('slug') for c in m.get('category', [])]: 
                    continue
                
                # 4. Phân loại chuẩn Phim Lẻ / Phim Bộ
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
                
    # Lưu file JSON riêng biệt cho từng mục
    output_path = os.path.join(OUTPUT_DIR, f"{filename}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results[:LIMIT_COUNT], f, ensure_ascii=False, separators=(',', ':'))
        
    return len(results[:LIMIT_COUNT])

if __name__ == "__main__":
    report = {}
    
    countries = [
        ("viet-nam", "Việt Nam", "viet"), 
        ("han-quoc", "Hàn Quốc", "han"), 
        ("trung-quoc", "Trung Quốc", "trung"), 
        ("au-my", "Âu Mỹ", "au_my"), 
        ("thai-lan", "Thái Lan", "thai")
    ]
    
    for c_slug, c_name, c_key in countries:
        report[f"le_{c_key}.json"] = crawl_country_logic(f"Lẻ {c_name}", f"le_{c_key}", c_slug, c_name, True)
        time.sleep(1) # Nghỉ giữa các danh mục để giải phóng luồng và IP
        
        report[f"bo_{c_key}.json"] = crawl_country_logic(f"Bộ {c_name}", f"bo_{c_key}", c_slug, c_name, False)
        time.sleep(1)
    
    print("\n" + "="*40 + "\n| BÁO CÁO PHIM QUỐC GIA CHUẨN |\n" + "-"*40)
    for k, v in report.items(): 
        print(f"| {k:22} | {v:11} |")
    print("="*40)
