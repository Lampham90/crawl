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
    results = []
    local_seen = set() 
    print(f"\n[Săn tìm] {target_name}...")
    
    # FIX: Nếu là 'phim-chieu-rap' thì API thực tế vẫn là 'phim-le'
    api_path = "phim-le" if endpoint == "phim-chieu-rap" else endpoint

    for year in YEARS:
        if len(results) >= TARGET_COUNT: break
        
        for page in range(1, 11): # Quét sâu 10 trang để đảm bảo CÓ phim
            if len(results) >= TARGET_COUNT: break
            
            url = f"{BASE_URL}/danh-sach/{api_path}"
            params = {"year": year, "page": page, "limit": 64}
            data = get_data(url, params)
            
            if not data or 'data' not in data or not data['data'].get('items'): break
                
            items = data['data']['items']
            slugs_to_fetch = [item['slug'] for item in items if item['slug'] not in local_seen]
            if not slugs_to_fetch: continue

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                details = list(executor.map(fetch_detail, slugs_to_fetch))

            for detail in details:
                if len(results) >= TARGET_COUNT: break
                if not detail or 'movie' not in detail: continue
                
                m = detail['movie']
                countries = [c.get('name') for c in m.get('country', [])]
                
                # Logic phân loại Lẻ/Bộ
                m_type = m.get('type', '')
                ep_total_val = str(m.get('episode_total', '1'))
                # Phim lẻ là type single HOẶC chỉ có 1 tập
                is_movie = (m_type == 'single' or ep_total_val == "1")

                match_country = True if not country_target else (country_target in countries)
                match_type = True
                if is_movie_logic is True and not is_movie: match_type = False
                if is_movie_logic is False and is_movie: match_type = False

                if match_country and match_type:
                    lang = str(m.get('lang', ''))
                    sub_display = "Lồng Tiếng" if "Lồng Tiếng" in lang else ("Thuyết Minh" if "Thuyết Minh" in lang else "Vietsub")
                    
                    results.append({
                        "name": m.get('name'),
                        "year": m.get('year'),
                        "slug": m.get('slug'),
                        "thumb": m.get('thumb_url'),
                        "poster": m.get('poster_url'),
                        "sub_type": sub_display,
                        "current_episode": m.get('episode_current', 'Full'),
                        "total_episodes": ep_total_val,
                        "country": countries[0] if countries else "",
                        "lang_raw": lang
                    })
                    local_seen.add(m.get('slug'))
            
            time.sleep(0.3) 
            if len(results) > 0:
                print(f"  + {year} - Trang {page}: {len(results)}/{TARGET_COUNT}")
                
    return results

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
