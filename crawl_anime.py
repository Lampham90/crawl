import requests
import json
import time
import os
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# --- CẤU HÌNH ---
BASE_URL = "https://phimapi.com/v1/api"
TARGET_COUNT = 15
MAX_WORKERS = 3
DATA_FILE = "data_all_lang_library.json"

def get_data(url, params=None):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        res = requests.get(url, params=params, timeout=15)
        if res.status_code == 200: return res.json()
    except: pass
    return None

def fetch_detail(slug):
    return get_data(f"https://phimapi.com/phim/{slug}")

def fetch_final(target_name, endpoint, country_target=None, is_movie_logic=None):
    results = []
    local_seen = set()
    print(f"> Đang quét: {target_name}...")
    
    for page in range(1, 6):
        if len(results) >= TARGET_COUNT: break
        
        url = f"{BASE_URL}/danh-sach/{endpoint}"
        params = {"page": page, "limit": 40}
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
            m_type = m.get('type', '')
            ep_total_val = str(m.get('episode_total', '1'))
            is_movie = (m_type == 'single' or ep_total_val == "1")

            if (not country_target or country_target in countries) and \
               (is_movie_logic is None or is_movie == is_movie_logic):
                
                lang = str(m.get('lang', ''))
                desc = m.get('content', '').replace('<p>', '').replace('</p>', '').replace('\n', ' ').strip()

                results.append({
                    "name": m.get('name'),
                    "year": m.get('year'),
                    "slug": m.get('slug'),
                    "thumb": m.get('thumb_url'),
                    "poster": m.get('poster_url'),
                    "sub_type": "Lồng Tiếng" if "Lồng Tiếng" in lang else ("Thuyết Minh" if "Thuyết Minh" in lang else "Vietsub"),
                    "current_episode": m.get('episode_current', 'Full'),
                    "total_episodes": ep_total_val,
                    "country": countries[0] if countries else "",
                    "description": desc
                })
                local_seen.add(m.get('slug'))
        time.sleep(0.2)
    return results

def main():
    start_time = time.time()
    final_data = {
        "anime_movie": [],
        "anime_nhat": [],
        "hh_trung_quoc": [],
        "phim_bo": [],
        "the_loai": {},
        "quoc_gia": {}
    }

    # Hốt hàng mới nhất không cần lọc năm
    final_data["anime_movie"] = fetch_final("Anime Movie", "hoat-hinh", is_movie_logic=True)
    final_data["anime_nhat"] = fetch_final("Anime Nhật", "hoat-hinh", country_target="Nhật Bản", is_movie_logic=False)
    final_data["hh_trung_quoc"] = fetch_final("HH Trung Quốc", "hoat-hinh", country_target="Trung Quốc", is_movie_logic=False)
    final_data["phim_bo"] = fetch_final("Phim Bộ Mới", "phim-bo")

    # Thể loại và Quốc gia mẫu
    final_data["quoc_gia"]["han-quoc"] = fetch_final("Phim Hàn", "phim-moi", country_target="Hàn Quốc")
    final_data["the_loai"]["kinh-di"] = fetch_final("Kinh Dị", "kinh-di")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)

    print(f"\n✅ Xong! Hoàn thành trong: {int(time.time() - start_time)}s")

if __name__ == "__main__":
    main()
