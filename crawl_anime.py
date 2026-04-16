import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "https://phimapi.com/v1/api"
YEARS = [2026, 2025]
TARGET_COUNT = 15
MAX_WORKERS = 10 # Số luồng chạy cùng lúc, để 10 là vừa đẹp không sợ bị khóa IP

def get_data(url, params=None):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return None

def fetch_detail(slug):
    """Hàm bổ trợ để lấy chi tiết 1 bộ phim (Dùng cho đa luồng)"""
    return get_data(f"https://phimapi.com/phim/{slug}")

def fetch_final(target_name, endpoint, country_target=None, is_movie_logic=None):
    results = []
    seen_slugs = set()
    print(f"\n[Săn tìm] {target_name}...")
    
    for year in YEARS:
        if len(results) >= TARGET_COUNT: break
        
        for page in range(1, 5): # Quét 4 trang đầu
            if len(results) >= TARGET_COUNT: break
            
            url = f"{BASE_URL}/danh-sach/{endpoint}?year={year}&page={page}&limit=64"
            data = get_data(url)
            
            if not data or 'data' not in data or not data['data'].get('items'):
                break
                
            items = data['data']['items']
            slugs_to_fetch = [item['slug'] for item in items if item['slug'] not in seen_slugs]

            # --- SỬ DỤNG ĐA LUỒNG ĐỂ LẤY CHI TIẾT PHIM ---
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                details = list(executor.map(fetch_detail, slugs_to_fetch))

            for detail in details:
                if len(results) >= TARGET_COUNT: break
                if not detail or 'movie' not in detail: continue
                
                m = detail['movie']
                countries = [c.get('name') for c in m.get('country', [])]
                
                ep_total_val = str(m.get('episode_total', '1'))
                status = str(m.get('episode_current', '')).lower()
                is_movie = (ep_total_val == "1" or "full" in status)

                match_country = True if not country_target else (country_target in countries)
                match_type = True
                if is_movie_logic is True and not is_movie: match_type = False
                if is_movie_logic is False and is_movie: match_type = False

                if match_country and match_type:
                    lang_raw = str(m.get('lang', ''))
                    sub_display = "Vietsub"
                    if "Lồng Tiếng" in lang_raw: sub_display = "Lồng Tiếng"
                    elif "Thuyết Minh" in lang_raw: sub_display = "Thuyết Minh"

                    results.append({
                        "name": m.get('name'),
                        "year": m.get('year'),
                        "slug": m.get('slug'),
                        "thumb": m.get('thumb_url'),
                        "poster": m.get('poster_url'),
                        "sub_type": sub_display,
                        "current_episode": m.get('episode_current', 'Full'),
                        "total_episodes": ep_total_val, # Thêm vào info như m yêu cầu
                        "country": countries[0] if countries else "",
                        "lang_raw": lang_raw
                    })
                    seen_slugs.add(m.get('slug'))
            
            print(f"  + Hoàn thành quét trang {page} - Đang có: {len(results)}/{TARGET_COUNT}")
            
    return results

def main():
    start_time = time.time()
    final_data = {}

    # 1. Nhóm Đặc biệt
    final_data["phim_moi"] = fetch_final("Phim Mới Cập Nhật", "phim-moi-cap-nhat")
    final_data["chieu_rap"] = fetch_final("Phim Chiếu Rạp", "phim-le", is_movie_logic=True)

    # 2. Nhóm Hoạt hình
    final_data["anime_movie"] = fetch_final("Anime Movie", "hoat-hinh", is_movie_logic=True)
    final_data["anime_nhat"] = fetch_final("Anime Nhật", "hoat-hinh", country_target="Nhật Bản", is_movie_logic=False)
    final_data["hh_trung_quoc"] = fetch_final("HH Trung Quốc", "hoat-hinh", country_target="Trung Quốc", is_movie_logic=False)

    # 3. Nhóm Quốc gia
    mapping = [
        ("Việt Nam", "vn"), ("Hàn Quốc", "han"), ("Trung Quốc", "trung"), 
        ("Âu Mỹ", "au_my"), ("Thái Lan", "thai")
    ]
    for c_name, c_key in mapping:
        final_data[f"le_{c_key}"] = fetch_final(f"Lẻ {c_name}", "phim-le", country_target=c_name, is_movie_logic=True)
        final_data[f"bo_{c_key}"] = fetch_final(f"Bộ {c_name}", "phim-bo", country_target=c_name, is_movie_logic=False)

    # 4. Top 10 & Sub/Dub pool
    final_data["top_10_bo"] = (final_data.get("bo_trung", [])[:4] + final_data.get("bo_han", [])[:3] + 
                               final_data.get("bo_au_my", [])[:2] + final_data.get("bo_thai", [])[:1])

    all_pool = []
    for v in final_data.values():
        if isinstance(v, list): all_pool.extend(v)
    
    unique_pool = {m['slug']: m for m in all_pool}.values()
    final_data["long_tieng"] = [m for m in unique_pool if "Lồng Tiếng" in m['lang_raw']][:15]
    final_data["thuyet_minh"] = [m for m in unique_pool if "Thuyết Minh" in m['lang_raw']][:15]

    with open("data_2026_perfect.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    
    end_time = time.time()
    print(f"\n[XONG] Tổng thời gian chạy: {int(end_time - start_time)} giây.")

if __name__ == "__main__":
    main()
