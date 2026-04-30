import requests, json, time, os
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "https://phimapi.com/v1/api"
LIMIT_COUNT = 400
MAX_WORKERS = 3 # Nâng lên để bào cho nhanh ní ơi
CRAWL_YEARS = [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017] # Danh sách năm cần bào
OUTPUT_DIR = "data_categories"

if not os.path.exists(OUTPUT_DIR): 
    os.makedirs(OUTPUT_DIR)

def get_data(url, params=None):
    try:
        res = requests.get(url, params=params, timeout=15)
        # Fix lỗi status code 200 mới là chuẩn
        return res.json() if res.status_code == 200 else None
    except: 
        return None

def fetch_detail(slug):
    # Fix lại link chi tiết chuẩn API v1
    return get_data(f"{BASE_URL}/phim/{slug}")

def crawl_by_year_logic(display_name, filename, endpoint, country=None, is_movie=None):
    results, seen = [], set()
    print(f"\n>>> Đang bào {display_name}...")
    
    for year in CRAWL_YEARS:
        if len(results) >= LIMIT_COUNT: break
        
        # Thêm vòng lặp trang để không sót phim (quét tối đa 5 trang mỗi năm)
        for page in range(1, 6):
            if len(results) >= LIMIT_COUNT: break
            
            params = {"year": year, "page": page, "limit": 64}
            data = get_data(f"{BASE_URL}/danh-sach/{endpoint}", params)
            
            # Nếu trang này không có dữ liệu thì nhảy sang năm kế tiếp
            if not data or 'data' not in data or not data['data'].get('items'):
                break
                
            items = data['data']['items']
            slugs = [it['slug'] for it in items if it['slug'] not in seen]
            
            if not slugs:
                continue

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                details = list(executor.map(fetch_detail, slugs))
                
            for d in details:
                if len(results) >= LIMIT_COUNT: break
                # API v1: Dữ liệu phim nằm trong d['data']['item']
                if not d or 'data' not in d or 'item' not in d['data']: continue
                
                m = d['data']['item']
                m_countries = [c.get('name') for c in m.get('country', [])]
                m_year = int(m.get('year', 0))
                
                # Logic phân loại Lẻ/Bộ
                is_actually_movie = (m.get('type') == 'single' or str(m.get('episode_total')) == "1")
                
                # Lọc theo điều kiện Quốc gia và Loại phim
                if country and country not in m_countries: continue
                if is_movie is not None and is_actually_movie != is_movie: continue
                
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
                seen.add(m['slug'])
            
            print(f"  - Đã hốt được {len(results)} phim (đang ở năm {year}, trang {page})")

    # Lưu file JSON
    with open(os.path.join(OUTPUT_DIR, f"{filename}.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, separators=(',', ':'))
    return len(results)

if __name__ == "__main__":
    start_time = time.time()
    report = {}
    
    # 1. Anime Movie (Hoạt hình + Phim lẻ)
    report['anime_movie.json'] = crawl_by_year_logic('Anime Movie', 'anime_movie', 'hoat-hinh', is_movie=True)
    
    # 2. Anime Nhật (Hoạt hình + Nhật Bản + Phim bộ)
    report['anime_nhat.json'] = crawl_by_year_logic('Anime Nhật', 'anime_nhat', 'hoat-hinh', country='Nhật Bản', is_movie=False)
    
    # 3. Hoạt hình Trung Quốc (Hoạt hình + Trung Quốc + Phim bộ)
    report['hh_trung_quoc.json'] = crawl_by_year_logic('HH Trung Quốc', 'hh_trung_quoc', 'hoat-hinh', country='Trung Quốc', is_movie=False)
    
    # 4. Phim Chiếu Rạp (Endpoint riêng)
    report['phim_chieu_rap.json'] = crawl_by_year_logic('Phim Chiếu Rạp', 'phim_chieu_rap', 'phim-chieu-rap')
    
    end_time = time.time()
    print("\n" + "="*45)
    print(f"| {'DANH MỤC':<25} | {'SỐ LƯỢNG':<10} |")
    print("-"*45)
    for k, v in report.items(): 
        print(f"| {k:<25} | {v:<10} |")
    print("="*45)
    print(f"Tổng thời gian bào: {round(end_time - start_time, 2)} giây.")
