import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# --- CẤU HÌNH ---
BASE_URL = "https://phimapi.com/v1/api"
TARGET_COUNT = 15
MAX_WORKERS = 5 # Tăng worker để bào info cho lẹ
DATA_FILE = "data_2026_perfect.json"

def get_data(url, params=None):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200: return res.json()
    except: pass
    return None

def fetch_detail(slug):
    # API này info chi tiết nằm ở /phim/{slug}
    return get_data(f"https://phimapi.com/phim/{slug}")

def fetch_final(target_name, endpoint, country_target=None, is_movie_logic=None):
    results = []
    local_seen = set()
    print(f"> Đang quét: {target_name}...")
    
    for page in range(1, 10):
        if len(results) >= TARGET_COUNT: break
        url = f"{BASE_URL}/danh-sach/{endpoint}"
        data = get_data(url, {"page": page, "limit": 40})
        
        if not data or 'data' not in data or not data['data'].get('items'): break
        items = data['data']['items']
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            details = list(executor.map(fetch_detail, [it['slug'] for it in items]))

        for detail in details:
            if len(results) >= TARGET_COUNT: break
            if not detail or 'movie' not in detail: continue
            m = detail['movie']
            if m['slug'] in local_seen: continue
            
            countries = [c.get('name') for c in m.get('country', [])]
            is_movie = (m.get('type') == 'single' or str(m.get('episode_total')) == "1")

            if (not country_target or country_target in countries) and \
               (is_movie_logic is None or is_movie == is_movie_logic):
                
                lang = m.get('lang', '')
                desc = m.get('content', '').replace('<p>', '').replace('</p>', '').replace('\n', ' ').strip()

                results.append({
                    "name": m.get('name'),
                    "year": int(m.get('year', 0)),
                    "slug": m.get('slug'),
                    "thumb": m.get('thumb_url'),
                    "poster": m.get('poster_url'),
                    "sub_type": "Lồng Tiếng" if "Lồng Tiếng" in lang else ("Thuyết Minh" if "Thuyết Minh" in lang else "Vietsub"),
                    "current_episode": m.get('episode_current', 'Full'),
                    "total_episodes": str(m.get('episode_total', '1')),
                    "country": countries[0] if countries else "",
                    "description": desc
                })
                local_seen.add(m['slug'])
    return results

def fetch_by_lang(lang_keyword, display_name):
    results = []
    local_seen = set()
    print(f"> Đang săn phim {display_name}...")

    # Quét sâu 20 trang để tìm bằng được lồng tiếng/thuyết minh
    for page in range(1, 21):
        if len(results) >= TARGET_COUNT: break
        url = f"{BASE_URL}/danh-sach/phim-moi"
        data = get_data(url, {"page": page, "limit": 40})
        
        if not data or 'data' not in data or not data['data'].get('items'): break
        items = data['data']['items']

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            details = list(executor.map(fetch_detail, [it['slug'] for it in items]))

        for detail in details:
            if len(results) >= TARGET_COUNT: break
            if not detail or 'movie' not in detail: continue
            m = detail['movie']
            if m['slug'] in local_seen: continue
            
            # QUAN TRỌNG: Kiểm tra từ khóa trong chuỗi lang (không phân biệt hoa thường)
            lang_str = m.get('lang', '')
            if lang_keyword.lower() in lang_str.lower():
                desc = m.get('content', '').replace('<p>', '').replace('</p>', '').replace('\n', ' ').strip()
                results.append({
                    "name": m.get('name'),
                    "year": int(m.get('year', 0)),
                    "slug": m.get('slug'),
                    "thumb": m.get('thumb_url'),
                    "poster": m.get('poster_url'),
                    "sub_type": display_name,
                    "current_episode": m.get('episode_current', 'Full'),
                    "total_episodes": str(m.get('episode_total', '1')),
                    "country": m.get('country', [{}])[0].get('name', ''),
                    "description": desc
                })
                local_seen.add(m['slug'])
    return results

def main():
    start_time = time.time()
    final_data = {}

    # Danh mục chính
    final_data["anime_movie"] = fetch_final("Anime Movie", "hoat-hinh", is_movie_logic=True)
    final_data["phim_chieu_rap"] = fetch_final("Phim Chiếu Rạp", "phim-chieu-rap")
    
    mapping = [("Việt Nam", "vn"), ("Hàn Quốc", "han"), ("Trung Quốc", "trung"), ("Âu Mỹ", "au_my")]
    for c_name, c_key in mapping:
        final_data[f"le_{c_key}"] = fetch_final(f"Lẻ {c_name}", "phim-le", country_target=c_name, is_movie_logic=True)
        final_data[f"bo_{c_key}"] = fetch_final(f"Bộ {c_name}", "phim-bo", country_target=c_name, is_movie_logic=False)

    # ĐÂY: Săn lùng Thuyết minh / Lồng tiếng
    final_data["long_tieng"] = fetch_by_lang("Lồng Tiếng", "Lồng Tiếng")
    final_data["thuyet_minh"] = fetch_by_lang("Thuyết Minh", "Thuyết Minh")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)

    print(f"\n✅ Xong! Tổng thời gian: {int(time.time() - start_time)}s")
    print(f"Lồng tiếng: {len(final_data['long_tieng'])} | Thuyết minh: {len(final_data['thuyet_minh'])}")

if __name__ == "__main__":
    main()
