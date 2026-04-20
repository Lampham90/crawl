    main()
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
MAX_WORKERS = 3 # Tăng nhẹ để hốt cho lẹ
DATA_FILE = "data_2026_perfect.json"

def get_data(url, params=None):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}
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
    
    # Quét khoảng 5 trang đầu để đảm bảo hốt đủ hàng mới nhất
    for page in range(1, 6): 
        if len(results) >= TARGET_COUNT: break
        
        url = f"{BASE_URL}/danh-sach/{endpoint}"
        # BỎ params 'year', chỉ lấy theo trang để hốt phim mới cập nhật
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
            
            # Lọc theo nước và loại phim (bộ/lẻ) nếu có yêu cầu, không check năm nữa
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
                    "year": m.get('year'), # Vẫn lấy năm để hiển thị trên App
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
        
        time.sleep(0.2) # Nghỉ ngắn giữa các trang
    return results

def main():
    start_time = time.time()
    final_data = {}

    # Ví dụ hốt vài danh mục tiêu biểu
    final_data["phim_bo_moi"] = fetch_final("Phim Bộ Mới", "phim-bo")
    final_data["phim_le_moi"] = fetch_final("Phim Lẻ Mới", "phim-le")
    final_data["hoat_hinh"] = fetch_final("Hoạt Hình", "hoat-hinh")
    final_data["han_quoc"] = fetch_final("Phim Hàn Quốc", "phim-moi", country_target="Hàn Quốc")

    # Lưu file
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)

    print(f"\n✅ Xong! Tổng thời gian: {int(time.time() - start_time)}s")

if __name__ == "__main__":
    main()
