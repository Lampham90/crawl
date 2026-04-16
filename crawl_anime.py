import requests
import json
import time
import os
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

BASE_URL = "https://phimapi.com/v1/api"
YEARS = [2026, 2025, 2024] 
TARGET_COUNT = 15
MAX_WORKERS = 6 # Theo ý m, chậm mà chắc
DATA_FILE = "data_2026_perfect.json"
TIME_FILE = "last_run.txt"

def get_data(url, params=None):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
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
    
    api_path = "phim-le" if endpoint == "phim-chieu-rap" else endpoint

    for year in YEARS:
        if len(results) >= TARGET_COUNT: break
        max_pages = 12 if year == 2026 else 5
        
        for page in range(1, max_pages + 1): 
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
                m_year = int(m.get('year', 0))
                countries = [c.get('name') for c in m.get('country', [])]
                m_type = m.get('type', '')
                ep_total_val = str(m.get('episode_total', '1'))
                is_movie = (m_type == 'single' or ep_total_val == "1")

                if (not country_target or country_target in countries) and \
                   (is_movie_logic is None or is_movie == is_movie_logic) and \
                   (m_year == year):
                    
                    lang = str(m.get('lang', ''))
                    results.append({
                        "name": m.get('name'),
                        "year": m_year,
                        "slug": m.get('slug'),
                        "thumb": m.get('thumb_url'),
                        "poster": m.get('poster_url'),
                        "sub_type": "Lồng Tiếng" if "Lồng Tiếng" in lang else ("Thuyết Minh" if "Thuyết Minh" in lang else "Vietsub"),
                        "current_episode": m.get('episode_current', 'Full'),
                        "total_episodes": ep_total_val,
                        "country": countries[0] if countries else "",
                        "lang_raw": lang
                    })
                    local_seen.add(m.get('slug'))
            time.sleep(0.3)
    return results

def interleave_trending(tr, han, au, thai):
    """Xen kẽ phim theo tỉ lệ 5:4:3:3"""
    trending = []
    # Biến đổi thành list để dùng pop(0)
    l_tr, l_han, l_au, l_thai = list(tr[:5]), list(han[:4]), list(au[:3]), list(thai[:3])
    
    while l_tr or l_han or l_au or l_thai:
        if l_tr: trending.append(l_tr.pop(0))
        if l_han: trending.append(l_han.pop(0))
        if l_au: trending.append(l_au.pop(0))
        if l_thai: trending.append(l_thai.pop(0))
    
    # Random nhẹ vị trí để không bị quá máy móc
    random.shuffle(trending)
    return trending[:15]

def main():
    start_time = time.time()
    
    # 1. Kiểm tra thời gian quét Trending
    should_update_trending = True
    if os.path.exists(TIME_FILE):
        with open(TIME_FILE, "r") as f:
            last_date = datetime.strptime(f.read().strip(), "%Y-%m-%d")
            if datetime.now() < last_date + timedelta(days=3):
                should_update_trending = False

    # 2. Đọc data cũ (nếu có) để giữ lại Trending
    old_data = {}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            old_data = json.load(f)

    final_data = {}
    # Danh mục chính luôn cập nhật
    final_data["phim_moi"] = fetch_final("Phim Mới", "phim-moi-cap-nhat")
    final_data["chieu_rap"] = fetch_final("Chiếu Rạp", "phim-le", is_movie_logic=True)
    final_data["anime_movie"] = fetch_final("Anime Movie", "hoat-hinh", is_movie_logic=True)
    final_data["anime_nhat"] = fetch_final("Anime Nhật", "hoat-hinh", country_target="Nhật Bản", is_movie_logic=False)
    final_data["hh_trung_quoc"] = fetch_final("HH Trung Quốc", "hoat-hinh", country_target="Trung Quốc", is_movie_logic=False)

    mapping = [("Việt Nam", "vn"), ("Hàn Quốc", "han"), ("Trung Quốc", "trung"), ("Âu Mỹ", "au_my"), ("Thái Lan", "thai")]
    for c_name, c_key in mapping:
        final_data[f"le_{c_key}"] = fetch_final(f"Lẻ {c_name}", "phim-le", country_target=c_name, is_movie_logic=True)
        final_data[f"bo_{c_key}"] = fetch_final(f"Bộ {c_name}", "phim-bo", country_target=c_name, is_movie_logic=False)

    # 3. Xử lý Logic Trending 3 ngày/lần
    if should_update_trending:
        print("\n[Hệ thống] Đã đến kỳ hạn 3 ngày. Đang cập nhật Top 15 Trending...")
        final_data["trending_phim_bo"] = interleave_trending(
            final_data.get("bo_trung", []), final_data.get("bo_han", []),
            final_data.get("bo_au_my", []), final_data.get("bo_thai", [])
        )
        with open(TIME_FILE, "w") as f:
            f.write(datetime.now().strftime("%Y-%m-%d"))
    else:
        print("\n[Hệ thống] Chưa đủ 3 ngày, giữ nguyên Trending cũ.")
        final_data["trending_phim_bo"] = old_data.get("trending_phim_bo", [])

    # Pool phụ
    all_pool = []
    for v in final_data.values():
        if isinstance(v, list): all_pool.extend(v)
    unique_pool = {m['slug']: m for m in all_pool}.values()
    final_data["long_tieng"] = [m for m in unique_pool if "Lồng Tiếng" in m['lang_raw']][:15]
    final_data["thuyet_minh"] = [m for m in unique_pool if "Thuyết Minh" in m['lang_raw']][:15]

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    
    print(f"\n[XONG] Tổng thời gian: {int(time.time() - start_time)}s.")

if __name__ == "__main__":
    main()
