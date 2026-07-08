import requests, json, os, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# --- CẤU HÌNH CHUẨN ---
BASE_URL = "https://phimapi.com/v1/api"
YEARS_FILTER = [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017]
LIMIT_COUNT = 300
MAX_WORKERS = 2  # Số luồng song song an toàn để không bị API chặn IP
OUTPUT_DIR = "data_categories"

if not os.path.exists(OUTPUT_DIR): 
    os.makedirs(OUTPUT_DIR)

def get_data(url, params=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        res = requests.get(url, params=params, headers=headers, timeout=15)
        if res.status_code == 200:
            return res.json()
    except: 
        pass
    return None

def fetch_detail(slug):
    time.sleep(0.05)  # Khoảng nghỉ siêu ngắn để API không bị ngộp request
    return get_data(f"{BASE_URL}/phim/{slug}")

def crawl_country_logic(display_name, filename, country_slug, country_filter, is_movie):
    results = []
    seen = set()  # Đảm bảo tập hợp slug làm mới hoàn toàn theo từng danh mục quốc gia
    
    print(f">>> Đang bào: {display_name}...")
    
    page = 1
    total_pages = 100
    
    # Vòng lặp lật trang vô hạn (cuốn chiếu) cho đến khi vét đủ 300 phim hoặc hết sạch trang từ API
    while page <= total_pages:
        # Nếu danh sách kết quả thực tế đã đạt đủ TARGET (300) -> Dừng lật trang ngay lập tức
        if len(results) >= LIMIT_COUNT:
            break
            
        url = f"{BASE_URL}/quoc-gia/{country_slug}"
        data = get_data(url, {"page": page, "limit": 64})
        
        if not data or 'data' not in data or not data['data'].get('items'): 
            break
            
        # Cập nhật tổng số trang thực tế từ phản hồi của API
        total_pages = int(data['data'].get('params', {}).get('pagination', {}).get('totalPages', 1))
        items = data['data']['items']
        
        # Gom danh sách slug mới của TRANG HIỆN TẠI
        slugs_in_page = []
        for it in items:
            slg = it['slug']
            if slg not in seen:
                seen.add(slg)
                slugs_in_page.append(slg)
        
        # Nếu trang hiện tại có slug mới, đẩy vào ThreadPool để kiểm tra chi tiết luôn
        if slugs_in_page:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                future_to_slug = {executor.submit(fetch_detail, slug): slug for slug in slugs_in_page}
                
                for future in as_completed(future_to_slug):
                    try:
                        d = future.result()
                        if not d or 'data' not in d or 'item' not in d['data']: 
                            continue
                        m = d['data']['item']
                        
                        # --- BỘ LỌC CHI TIẾT ---
                        # 1. Lọc đúng các năm trong cấu hình (2017 - 2026)
                        m_year = int(m.get('year', 0))
                        if m_year not in YEARS_FILTER: 
                            continue
                        
                        # 2. Loại bỏ Trailer / Sắp ra mắt / Tập 0
                        ep_current = str(m.get('episode_current', '')).lower()
                        if any(x in ep_current for x in ["trailer", "sắp ra mắt", "coming soon", "tập 0"]): 
                            continue
                            
                        # 3. Loại bỏ phim Hoạt hình
                        if 'hoat-hinh' in [c.get('slug') for c in m.get('category', [])]: 
                            continue
                        
                        # 4. Phân loại chuẩn xác Phim Lẻ (single) / Phim Bộ (series)
                        is_actually_movie = (m.get('type') == 'single' or str(m.get('episode_total')) == "1")
                        if is_actually_movie != is_movie: 
                            continue
                        
                        results.append({
                            "name": m.get('name'), 
                            "year": m_year, 
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
                        
        print(f"    -> Đang quét trang {page}/{total_pages}... Thu về {len(results)} Phim hợp lệ.")
        page += 1
        time.sleep(0.15)  # Nghỉ ngắn giữa các trang tránh kích hoạt DDoS Firewall của API
                
    # --- LOGIC SẮP XẾP CHUẨN NĂM ---
    # Ép dữ liệu phải xếp hàng ngay ngắn theo Năm giảm dần (2026 xuôi về 2017)
    results.sort(key=lambda x: x['year'], reverse=True)
    
    # Cắt lấy chính xác số lượng phim quy định
    final_results = results[:LIMIT_COUNT]
    
    # Xuất file JSON riêng biệt cho từng danh mục danh sách
    output_path = os.path.join(OUTPUT_DIR, f"{filename}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_results, f, ensure_ascii=False, separators=(',', ':'))
        
    return len(final_results)

if __name__ == "__main__":
    start_time = time.time()
    report = {}
    
    # Cấu hình danh mục Quốc gia chuẩn theo API slug
    countries = [
        ("viet-nam", "Việt Nam", "vn"), 
        ("han-quoc", "Hàn Quốc", "han"), 
        ("trung-quoc", "Trung Quốc", "trung"), 
        ("au-my", "Âu Mỹ", "au_my"), 
        ("thai-lan", "Thái Lan", "thai")
    ]
    
    for c_slug, c_name, c_key in countries:
        # Cào & xuất file Phim Lẻ (ví dụ: le_han.json)
        report[f"le_{c_key}.json"] = crawl_country_logic(f"Lẻ {c_name}", f"le_{c_key}", c_slug, c_name, True)
        time.sleep(0.5)
        
        # Cào & xuất file Phim Bộ (ví dụ: bo_han.json)
        report[f"bo_{c_key}.json"] = crawl_country_logic(f"Bộ {c_name}", f"bo_{c_key}", c_slug, c_name, False)
        time.sleep(0.5)
    
    print("\n" + "="*45 + f"\n| BÁO CÁO HOÀN TẤT CRAWL KHÔNG SÓT PHIM |\n" + "-"*45)
    for k, v in report.items(): 
        print(f"| {k:22} | {v:14} phim |")
    print("="*45)
    print(f"Tổng thời gian xử lý: {int(time.time() - start_time)} giây.\n")
