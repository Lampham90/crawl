import requests, json, time, os
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "https://phimapi.com/v1/api"
LIMIT_COUNT = 10
MAX_WORKERS = 2
# Danh sách năm ní muốn test lọc
TEST_YEARS = [2026, 2025, 2024] 
OUTPUT_DIR = "data_categories"

if not os.path.exists(OUTPUT_DIR): 
    os.makedirs(OUTPUT_DIR)

def get_data(url, params=None):
    try:
        res = requests.get(url, params=params, timeout=15)
        return res.json() if res.status_code == 200 else None
    except: 
        return None

def fetch_detail(slug):
    return get_data(f"https://phimapi.com/phim/{slug}")

def crawl_anime_by_year(display_name, filename, country=None, is_movie=None):
    results, seen = [], set()
    print(f">>> Đang test lọc {display_name} theo năm...")
    
    for year in TEST_YEARS:
        if len(results) >= LIMIT_COUNT: break
        
        # Gọi API theo danh mục hoạt hình và lọc theo năm
        # Lưu ý: API phimapi hỗ trợ tham số year trong endpoint danh-sach
        params = {"year": year, "page": 1, "limit": 64}
        data = get_data(f"{BASE_URL}/danh-sach/hoat-hinh", params)
        
        if not data or 'data' not in data or data['data'].get('items') is None:
            continue
            
        items = data['data']['items']
        slugs = [it['slug'] for it in items if it['slug'] not in seen]
        
        if not slugs: continue

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            details = list(executor.map(fetch_detail, slugs))
            
        for d in details:
            if len(results) >= LIMIT_COUNT: break
            if not d or 'movie' not in d: continue
            
            m = d['movie']
            m_countries = [c.get('name') for c in m.get('country', [])]
            m_year = int(m.get('year', 0))
            
            # Kiểm tra loại phim (Lẻ/Bộ)
            is_actually_movie = (m.get('type') == 'single' or str(m.get('episode_total')) == "1")
            
            # Lọc điều kiện
            if country and country not in m_countries: continue
            if is_movie is not None and is_actually_movie != is_movie: continue
            # Check lại năm một lần nữa cho chắc
            if m_year != year: continue 
            
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
            
    with open(os.path.join(OUTPUT_DIR, f"{filename}.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, separators=(',', ':'))
    return len(results)

if __name__ == "__main__":
    report = {}
    
    # Test 3 mục Anime
    report['anime_movie.json'] = crawl_anime_by_year('Anime Movie', 'anime_movie', is_movie=True)
    report['anime_nhat.json'] = crawl_anime_by_year('Anime Nhật', 'anime_nhat', country='Nhật Bản', is_movie=False)
    report['hh_trung_quoc.json'] = crawl_anime_by_year('HH Trung Quốc', 'hh_trung_quoc', country='Trung Quốc', is_movie=False)
    
    print("\n" + "="*35 + "\n| BÁO CÁO TEST LỌC NĂM |\n" + "-"*35)
    for k, v in report.items(): 
        print(f"| {k:20} | {v:7} |")
    print("="*35)
