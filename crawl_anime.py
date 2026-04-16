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
    
    api_path = "phim-le" if endpoint == "phim-chieu-rap" else endpoint

    for year in YEARS:
        if len(results) >= TARGET_COUNT: break
        
        # Năm 2026 quét sâu hơn (15 trang) để ưu tiên lấy hàng mới nhất
        max_pages = 15 if year == 2026 else 5
        
        for page in range(1, max_pages + 1): 
            if len(results) >= TARGET_COUNT: break
            
            url = f"{BASE_URL}/danh-sach/{api_path}"
            params = {"year": year, "page": page, "limit": 64}
            data = get_data(url, params)
            
            if not data or 'data' not in data or not data['data'].get('items'): break
                
            items = data['data']['items']
            slugs_to_fetch = [item['slug'] for item in items if item['slug'] not in local_seen]
            if not slugs_to_fetch: continue

            # Lấy chi tiết song song
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                details = list(executor.map(fetch_detail, slugs_to_fetch))

            for detail in details:
                if len(results) >= TARGET_COUNT: break
                if not detail or 'movie' not in detail: continue
                
                m = detail['movie']
                
                # Ép kiểu year về int để so sánh chính xác
                m_year = int(m.get('year', 0))
                countries = [c.get('name') for c in m.get('country', [])]
                
                m_type = m.get('type', '')
                ep_total_val = str(m.get('episode_total', '1'))
                is_movie = (m_type == 'single' or ep_total_val == "1")

                # BỘ LỌC CHÍNH
                match_country = True if not country_target else (country_target in countries)
                match_type = True
                if is_movie_logic is True and not is_movie: match_type = False
                if is_movie_logic is False and is_movie: match_type = False
                
                # KIỂM TRA NĂM: Phải đúng năm đang quét (tránh API trả về phim cũ ở trang mới)
                if match_country and match_type and m_year == year:
                    lang = str(m.get('lang', ''))
                    sub_display = "Lồng Tiếng" if "Lồng Tiếng" in lang else ("Thuyết Minh" if "Thuyết Minh" in lang else "Vietsub")
                    
                    results.append({
                        "name": m.get('name'),
                        "year": m_year,
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
            
            # Log tiến độ theo từng trang để m dễ theo dõi
            if len(results) > 0:
                print(f"  + {year} - Trang {page}: Đã lấy {len(results)}/{TARGET_COUNT}")
            
            time.sleep(0.2) # Nghỉ nhẹ tránh block
                
    return results

def main():
    start_time = time.time()
    final_data = {}

    # Chạy lần lượt các danh mục
    final_data["phim_moi"] = fetch_final("Phim Mới", "phim-moi-cap-nhat")
    final_data["chieu_rap"] = fetch_final("Chiếu Rạp", "phim-le", is_movie_logic=True)
    final_data["anime_movie"] = fetch_final("Anime Movie", "hoat-hinh", is_movie_logic=True)
    final_data["anime_nhat"] = fetch_final("Anime Nhật", "hoat-hinh", country_target="Nhật Bản", is_movie_logic=False)
    final_data["hh_trung_quoc"] = fetch_final("HH Trung Quốc", "hoat-hinh", country_target="Trung Quốc", is_movie_logic=False)

    mapping = [("Việt Nam", "vn"), ("Hàn Quốc", "han"), ("Trung Quốc", "trung"), ("Âu Mỹ", "au_my"), ("Thái Lan", "thai")]
    for c_name, c_key in mapping:
        final_data[f"le_{c_key}"] = fetch_final(f"Lẻ {c_name}", "phim-le", country_target=c_name, is_movie_logic=True)
        final_data[f"bo_{c_key}"] = fetch_final(f"Bộ {c_name}", "phim-bo", country_target=c_name, is_movie_logic=False)

    # Tổng hợp các mục phụ từ pool đã có
    all_pool = []
    for v in final_data.values():
        if isinstance(v, list): all_pool.extend(v)
    
    unique_pool = {m['slug']: m for m in all_pool}.values()
    final_data["long_tieng"] = [m for m in unique_pool if "Lồng Tiếng" in m['lang_raw']][:15]
    final_data["thuyet_minh"] = [m for m in unique_pool if "Thuyết Minh" in m['lang_raw']][:15]

    with open("data_2026_perfect.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    
    print(f"\n[XONG] Tổng thời gian: {int(time.time() - start_time)}s. Check file ngay!")

if __name__ == "__main__":
    main()
