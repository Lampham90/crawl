import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "https://phimapi.com/v1/api"
YEARS = [2026, 2025, 2024] 
TARGET_COUNT = 15
MAX_WORKERS = 10 

def get_data(url, params=None):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200: return res.json()
    except: pass
    return None

def fetch_detail(slug):
    return get_data(f"https://phimapi.com/phim/{slug}")

def fetch_final(target_name, endpoint, country_target=None, is_movie_logic=None):
    all_potential_movies = [] # Chứa tất cả phim tìm được trước khi lọc
    local_seen = set() 
    print(f"\n[Săn tìm] {target_name}...")
    
    api_path = "phim-le" if endpoint == "phim-chieu-rap" else endpoint

    # Bước 1: Thu thập slug từ TẤT CẢ các năm trước
    all_slugs = []
    for year in YEARS:
        for page in range(1, 4): # Quét 3 trang đầu mỗi năm để lấy slug
            url = f"{BASE_URL}/danh-sach/{api_path}"
            params = {"year": year, "page": page, "limit": 64}
            data = get_data(url, params)
            if data and 'data' in data:
                items = data['data'].get('items', [])
                all_slugs.extend([it['slug'] for it in items if it['slug'] not in local_seen])
                for it in items: local_seen.add(it['slug'])

    # Bước 2: Lấy chi tiết đa luồng cho đống slug vừa tìm được
    if not all_slugs: return []
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        details = list(executor.map(fetch_detail, all_slugs))

    # Bước 3: Lọc và ƯU TIÊN NĂM CAO NHẤT
    valid_movies = []
    for detail in details:
        if not detail or 'movie' not in detail: continue
        m = detail['movie']
        
        # Logic lọc quốc gia & loại phim (giữ nguyên như cũ)
        countries = [c.get('name') for c in m.get('country', [])]
        m_type = m.get('type', '')
        ep_total_val = str(m.get('episode_total', '1'))
        is_movie = (m_type == 'single' or ep_total_val == "1")

        if (not country_target or country_target in countries) and \
           (is_movie_logic is None or is_movie == is_movie_logic):
            
            lang = str(m.get('lang', ''))
            valid_movies.append({
                "name": m.get('name'),
                "year": int(m.get('year', 0)), # Chuyển về int để sort
                "slug": m.get('slug'),
                "thumb": m.get('thumb_url'),
                "poster": m.get('poster_url'),
                "sub_type": "Lồng Tiếng" if "Lồng Tiếng" in lang else ("Thuyết Minh" if "Thuyết Minh" in lang else "Vietsub"),
                "current_episode": m.get('episode_current', 'Full'),
                "total_episodes": ep_total_val,
                "country": countries[0] if countries else "",
                "lang_raw": lang
            })

    # Bước 4: Sắp xếp theo năm giảm dần (2026 -> 2025 -> 2024)
    valid_movies.sort(key=lambda x: x['year'], reverse=True)
    
    # Bước 5: Lấy đúng 15 con đầu bảng
    final_selection = valid_movies[:TARGET_COUNT]
    print(f"  + Tổng kết: Lấy được {len(final_selection)} phim (Ưu tiên năm mới nhất)")
    
    return final_selection

def main():
    start_time = time.time()
    final_data = {}

    # Dùng đúng các Endpoint mà API v1 hỗ trợ
    final_data["phim_moi"] = fetch_final("Phim Mới", "phim-moi-cap-nhat")
    final_data["chieu_rap"] = fetch_final("Chiếu Rạp", "phim-le", is_movie_logic=True)
    final_data["anime_movie"] = fetch_final("Anime Movie", "hoat-hinh", is_movie_logic=True)
    final_data["anime_nhat"] = fetch_final("Anime Nhật", "hoat-hinh", country_target="Nhật Bản", is_movie_logic=False)
    final_data["hh_trung_quoc"] = fetch_final("HH Trung Quốc", "hoat-hinh", country_target="Trung Quốc", is_movie_logic=False)

    mapping = [("Việt Nam", "vn"), ("Hàn Quốc", "han"), ("Trung Quốc", "trung"), ("Âu Mỹ", "au_my"), ("Thái Lan", "thai")]
    for c_name, c_key in mapping:
        final_data[f"le_{c_key}"] = fetch_final(f"Lẻ {c_name}", "phim-le", country_target=c_name, is_movie_logic=True)
        final_data[f"bo_{c_key}"] = fetch_final(f"Bộ {c_name}", "phim-bo", country_target=c_name, is_movie_logic=False)

    # Pool tổng hợp Top 10 & Dub/Sub
    all_pool = []
    for v in final_data.values():
        if isinstance(v, list): all_pool.extend(v)
    
    unique_pool = {m['slug']: m for m in all_pool}.values()
    final_data["long_tieng"] = [m for m in unique_pool if "Lồng Tiếng" in m['lang_raw']][:15]
    final_data["thuyet_minh"] = [m for m in unique_pool if "Thuyết Minh" in m['lang_raw']][:15]

    with open("data_2026_perfect.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    
    print(f"\n[XONG] Tổng thời gian: {int(time.time() - start_time)}s. Quá mượt!")

if __name__ == "__main__":
    main()
