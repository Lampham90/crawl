import requests, json, os, time

# --- CẤU HÌNH ---
BASE_URL = "https://phimapi.com/v1/api"
YEARS_FILTER = [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017]
LIMIT_TOTAL = 300
OUTPUT_DIR = "data_categories"

if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

def get_data(url, params=None):
    try:
        # Tăng timeout để tránh lỗi khi server API phản hồi chậm
        res = requests.get(url, params=params, timeout=15)
        if res.status_code == 200: return res.json()
    except: pass
    return None

def crawl_category(display_name, filename, country_slug, is_movie):
    results = []
    seen = set()
    page = 1
    
    print(f">>> Đang bào: {display_name}...")
    
    # Vòng lặp lấy trang
    while len(results) < LIMIT_TOTAL:
        url = f"{BASE_URL}/quoc-gia/{country_slug}"
        data = get_data(url, {"page": page, "limit": 64})
        
        if not data or not data.get('data') or not data['data'].get('items'):
            break
            
        items = data['data']['items']
        
        for item in items:
            if len(results) >= LIMIT_TOTAL: break
            
            # Kiểm tra loại phim (single: phim lẻ, series: phim bộ)
            # Lưu ý: Một số phim có thể không có trường 'type', dùng 'episode_total' để check nếu cần
            item_type = item.get('type')
            is_single = (item_type == 'single')
            
            # Bộ lọc chính
            if is_single != is_movie: continue
            
            m_year = int(item.get('year', 0))
            if m_year not in YEARS_FILTER: continue
            
            if item['slug'] not in seen:
                seen.add(item['slug'])
                 results.append({
                    "name": m.get('name'), 
                    "year": m_year, 
                    "slug": m.get('slug'), 
                    "thumb": m.get('thumb_url'), 
                    "poster": m.get('poster_url'), 
                    "sub_type": m.get('lang', 'Vietsub'), 
                    "current_episode": m.get('episode_current', 'Full'), 
                    "total_episodes": str(m.get('episode_total', '1')), 
                    "country": m_countries[0] if m_countries else ""
                })
        
        print(f"    - Trang {page} | Thu thập: {len(results)}/{LIMIT_TOTAL}")
        page += 1
        time.sleep(0.5) # Nghỉ lâu hơn một chút để giữ kết nối ổn định
        
    # Lưu file
    with open(os.path.join(OUTPUT_DIR, f"{filename}.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    
    return len(results)

if __name__ == "__main__":
    # Danh sách các quốc gia đầy đủ
    countries = [
        ("viet-nam", "vn"), ("han-quoc", "han"), ("trung-quoc", "trung"), 
        ("au-my", "au_my"), ("thai-lan", "thai")
    ]
    
    report = {}
    for c_slug, c_key in countries:
        report[f"le_{c_key}.json"] = crawl_category(f"Lẻ {c_key}", f"le_{c_key}", c_slug, True)
        report[f"bo_{c_key}.json"] = crawl_category(f"Bộ {c_key}", f"bo_{c_key}", c_slug, False)
        
    print("\n--- HOÀN TẤT ---")
    print(report)
