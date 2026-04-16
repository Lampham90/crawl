import requests
import json
import time

BASE_URL = "https://phimapi.com/v1/api"
YEARS = [2026, 2025]
TARGET = 2 # Mỗi loại lấy đúng 2 phim để test cho nhanh

def get_data(url, params=None):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return None

def fetch_traditional(target_name, endpoint, country_target=None, is_movie_logic=None):
    results = []
    print(f"\n[Săn tìm] {target_name}...")
    
    for year in YEARS:
        if len(results) >= TARGET: break
        
        # Thử quét 3 trang đầu của danh mục đó
        for page in range(1, 4):
            if len(results) >= TARGET: break
            
            url = f"{BASE_URL}/danh-sach/{endpoint}?year={year}&page={page}&limit=64"
            data = get_data(url)
            
            if not data or 'data' not in data or not data['data'].get('items'):
                break
                
            for item in data['data']['items']:
                if len(results) >= TARGET: break
                
                # Lấy detail để kiểm tra quốc gia và loại phim (JSON m gửi nằm ở đây)
                detail = get_data(f"https://phimapi.com/phim/{item['slug']}")
                if not detail or 'movie' not in detail: continue
                
                m = detail['movie']
                
                # 1. Lấy danh sách quốc gia
                countries = [c.get('name') for c in m.get('country', [])]
                # 2. Kiểm tra logic phim lẻ/bộ
                ep_total = str(m.get('episode_total', '1'))
                status = str(m.get('episode_current', '')).lower()
                is_movie = (ep_total == "1" or "full" in status)

                # --- BỘ LỌC TRUYỀN THỐNG ---
                match_country = True if not country_target else (country_target in countries)
                match_type = True
                if is_movie_logic is True and not is_movie: match_type = False
                if is_movie_logic is False and is_movie: match_type = False

                if match_country and match_type:
                    results.append(m.get('name'))
                    print(f"  + Thành công: {m.get('name')} ({year}) [{', '.join(countries)}]")
                    
                time.sleep(0.05) # Tránh bị block
    return results

def main():
    final_results = {}

    # 1. Nhóm Hoạt hình
    final_results["anime_movie"] = fetch_traditional("Anime Movie", "hoat-hinh", is_movie_logic=True)
    final_results["anime_nhat"] = fetch_traditional("Anime Nhật (Bộ)", "hoat-hinh", country_target="Nhật Bản", is_movie_logic=False)
    final_results["hh_trung_quoc"] = fetch_traditional("HH Trung Quốc (Bộ)", "hoat-hinh", country_target="Trung Quốc", is_movie_logic=False)

    # 2. Nhóm Quốc gia
    mapping = [
        ("Việt Nam", "vn"), ("Hàn Quốc", "han"), ("Trung Quốc", "trung"), 
        ("Âu Mỹ", "au_my"), ("Thái Lan", "thai")
    ]

    for c_name, c_key in mapping:
        # Lấy 2 phim lẻ của quốc gia này
        final_results[f"le_{c_key}"] = fetch_traditional(f"Phim Lẻ {c_name}", "phim-le", country_target=c_name)
        # Lấy 2 phim bộ của quốc gia này
        final_results[f"bo_{c_key}"] = fetch_traditional(f"Phim Bộ {c_name}", "phim-bo", country_target=c_name)

    # Xuất kết quả
    print("\n========= TỔNG KẾT TEST =========")
    print(json.dumps(final_results, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    main()
