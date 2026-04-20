import requests
import json
import time
import os
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# --- CẤU HÌNH ---
BASE_URL = "https://phimapi.com/v1/api"
TARGET_COUNT = 20 # Tăng nhẹ số lượng lấy mỗi mục cho xôm
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
    print(f"> Đang hốt mới nhất: {target_name}...")
    
    # Chỉ lật khoảng 3 trang đầu để lấy phim mới cập nhật nhất
    for page in range(1, 4): 
        if len(results) >= TARGET_COUNT: break
        
        url = f"{BASE_URL}/danh-sach/{endpoint}"
        # Bỏ params year, chỉ lấy phim mới nhất (mặc định API trả về theo thời gian cập nhật)
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
            
            # Logic lọc theo nước và loại phim (bộ/lẻ) nếu có yêu cầu
            countries = [c.get('name') for c in m.get('country', [])]
            m_type = m.get('type', '')
            ep_total_val = str(m.get('episode_total', '1'))
            is_movie = (m_type == 'single' or ep_total_val == "1")

            # Chỉ lọc theo Quốc gia hoặc Loại phim, KHÔNG lọc năm
            if (not country_target or country_target in countries) and \
               (is_movie_logic is None or is_movie == is_movie_logic):
                
                lang = str(m.get('lang', ''))
                results.append({
                    "name": m.get('name'),
                    "year": m.get('year'), # Vẫn lấy năm để hiện lên App nhưng ko dùng để lọc
                    "slug": m.get('slug'),
                    "thumb": m.get('thumb_url'),
                    "poster": m.get('poster_url'),
                    "sub_type": "Lồng Tiếng" if "Lồng Tiếng" in lang else ("Thuyết Minh" if "Thuyết Minh" in lang else "Vietsub"),
                    "current_episode": m.get('episode_current', 'Full'),
                    "total_episodes": ep_total_val,
                    "country": countries[0] if countries else ""
                })
                local_seen.add(m.get('slug'))
        time.sleep(0.2)
    return results

def main():
    start_time = time.time()
    final_data = {
        "all_long_tieng": [],
        "all_thuyet_minh": [],
        "phim_bo": [],
        "the_loai": {},
        "quoc_gia": {}
    }

    # 1. Lấy phim Bộ mới nhất
    final_data["phim_bo"] = fetch_final("Phim Bộ Mới", "phim-bo")

    # 2. Lấy theo Quốc gia (Mới nhất, ko quan tâm năm)
    countries_map = [("Hàn Quốc", "han-quoc"), ("Trung Quốc", "trung-quoc"), ("Âu Mỹ", "au-my")]
    for name, slug in countries_map:
        final_data["quoc_gia"][slug] = fetch_final(f"Phim {name}", "phim-moi", country_target=name)

    # 3. Lấy theo Thể loại
    categories_map = [("Hoạt Hình", "hoat-hinh"), ("Kinh Dị", "kinh-di")]
    for name, slug in categories_map:
        final_data["the_loai"][slug] = fetch_final(name, slug)

    # Lưu file
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)

    print(f"\n✅ Xong! Tổng thời gian: {int(time.time() - start_time)}s")

if __name__ == "__main__":
    main()
