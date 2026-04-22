import requests
import json
import time
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# --- CẤU HÌNH ---
BASE_URL = "https://phimapi.com/v1/api"
TARGET_COUNT = 15
MAX_WORKERS = 3  # Tăng nhẹ để nhanh hơn
DATA_FILE = "data_2026_perfect.json"

def get_data(url, params=None):
    headers = {
        "User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(110, 120)}.0.0.0 Safari/537.36"
    }
    try:
        res = requests.get(url, params=params, timeout=20)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"Lỗi kết nối: {e}")
    return None

def fetch_detail(slug):
    # Endpoint chi tiết phim thường ổn định hơn v1/api
    return get_data(f"https://phimapi.com/phim/{slug}")

def fetch_data_v2(target_name, type_filter=None, country_filter=None, is_movie=None, lang_filter=None):
    results = []
    seen = set()
    print(f"> Đang xử lý: {target_name}...")

    # Quét sâu qua các trang của phim mới cập nhật để lọc
    for page in range(1, 30): 
        if len(results) >= TARGET_COUNT:
            break
            
        # Dùng endpoint phim-moi-cap-nhat là endpoint "sống" dai nhất của API này
        url = f"https://phimapi.com/danh-sach/phim-moi-cap-nhat"
        data = get_data(url, params={"page": page})
        
        if not data or 'items' not in data:
            break
            
        items = data['items']
        slugs = [it['slug'] for it in items if it['slug'] not in seen]
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            details = list(executor.map(fetch_detail, slugs))

        for detail in details:
            if len(results) >= TARGET_COUNT: break
            if not detail or 'movie' not in detail: continue
            
            m = detail['movie']
            m_type = m.get('type', '')
            countries = [c.get('name') for c in m.get('country', [])]
            lang = str(m.get('lang', '')).lower()
            ep_total = str(m.get('episode_total', '1'))
            
            # Logic kiểm tra Movie/Series
            check_is_movie = (m_type == 'single' or ep_total == "1")

            # Bộ lọc tổng hợp
            match = True
            if type_filter and type_filter not in m_type: match = False
            if country_filter and country_filter not in countries: match = False
            if is_movie is not None and check_is_movie != is_movie: match = False
            if lang_filter:
                if lang_filter not in lang: match = False

            if match:
                results.append({
                    "name": m.get('name'),
                    "year": m.get('year', 0),
                    "slug": m.get('slug'),
                    "thumb": m.get('thumb_url'),
                    "poster": m.get('poster_url'),
                    "sub_type": "Lồng Tiếng" if "lồng tiếng" in lang else ("Thuyết Minh" if "thuyết minh" in lang else "Vietsub"),
                    "current_episode": m.get('episode_current', 'Full'),
                    "total_episodes": ep_total,
                    "country": countries[0] if countries else "",
                    "description": m.get('content', '').replace('<p>', '').replace('</p>', '').replace('\n', ' ').strip()
                })
                seen.add(m.get('slug'))
        
        time.sleep(0.1) # Nghỉ cực ngắn để tránh 0s
    return results

def main():
    start_time = time.time()
    final_data = {}
    
    # Định nghĩa danh sách cần hốt
    jobs = [
        ("anime_movie", "Anime Lẻ", "hoat-hinh", None, True, None),
        ("anime_nhat", "Anime Nhật", "hoat-hinh", "Nhật Bản", False, None),
        ("phim_chieu_rap", "Phim Chiếu Rạp", "single", None, True, None),
        ("le_vn", "Lẻ Việt Nam", "single", "Việt Nam", True, None),
        ("bo_han", "Bộ Hàn Quốc", "series", "Hàn Quốc", False, None),
        ("bo_trung", "Bộ Trung Quốc", "series", "Trung Quốc", False, None),
        ("long_tieng", "Phim Lồng Tiếng", None, None, None, "lồng tiếng"),
        ("thuyet_minh", "Phim Thuyết Minh", None, None, None, "thuyết minh"),
    ]

    for key, name, t_filter, c_filter, is_m, l_filter in jobs:
        final_data[key] = fetch_data_v2(name, t_filter, c_filter, is_m, l_filter)
        print(f"--- Đã xong {name}: {len(final_data[key])} phim")

    # Lưu file
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)

    print(f"\n[OK] Tổng thời gian: {int(time.time() - start_time)}s")
    print(f"File lưu tại: {DATA_FILE}")

if __name__ == "__main__":
    main()
