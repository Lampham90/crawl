import requests
import json
import time
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# --- CẤU HÌNH ---
BASE_URL = "https://phimapi.com/v1/api"
YEARS = [2026, 2025, 2024, 2023, 2022] # Quét sâu để đủ 200 phim
LIMIT_COUNT = 200
MAX_WORKERS = 5 # Tăng tốc độ bào dữ liệu
OUTPUT_DIR = "data_categories"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def get_data(url, params=None):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        res = requests.get(url, params=params, timeout=15)
        if res.status_code == 200: return res.json()
    except: pass
    return None

def fetch_detail(slug):
    return get_data(f"https://phimapi.com/phim/{slug}")

def crawl_category(display_name, filename, endpoint, country=None, is_movie=None, category=None, is_anime=False, lang_key=None):
    results = []
    seen = set()
    print(f"\n>>> ĐANG BÀO MỤC: {display_name} (Mục tiêu {LIMIT_COUNT} phim)")

    for year in YEARS:
        if len(results) >= LIMIT_COUNT: break
        
        # Quyết định dùng endpoint nào
        if endpoint in ['hoat-hinh', 'phim-chieu-rap', 'phim-le', 'phim-bo', 'tv-shows']:
            url = f"{BASE_URL}/danh-sach/{endpoint}"
            params = {"year": year, "page": 1, "limit": 64}
        else: # Cho các mục lọc theo Thể loại (Kinh dị, Hài...) hoặc Năm
            url = f"{BASE_URL}/nam/{year}"
            params = {"page": 1, "limit": 64, "sort_field": "modified.time"}
            if category: params['category'] = category
            if lang_key: params['sort_lang'] = lang_key

        for page in range(1, 15): # Quét sâu trang để lấy đủ
            if len(results) >= LIMIT_COUNT: break
            params['page'] = page
            data = get_data(url, params)
            
            if not data or 'data' not in data or not data['data'].get('items'): break
            items = data['data']['items']
            
            # Lấy info chi tiết để lọc gắt
            slugs_to_fetch = [it['slug'] for it in items if it['slug'] not in seen]
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                details = list(executor.map(fetch_detail, slugs_to_fetch))

            for detail in details:
                if len(results) >= LIMIT_COUNT: break
                if not detail or 'movie' not in detail: continue
                m = detail['movie']
                
                # --- LOGIC LỌC CHÍNH ---
                m_type = m.get('type', '')
                is_actually_movie = (m_type == 'single' or str(m.get('episode_total')) == "1")
                m_countries = [c.get('name') for c in m.get('country', [])]
                m_cats = [c.get('slug') for c in m.get('category', [])]
                
                # 1. Lọc Hoạt hình/Anime: Nếu không phải yêu cầu anime, thì phim không được chứa category 'hoat-hinh'
                if not is_anime and 'hoat-hinh' in m_cats: continue
                if is_anime and 'hoat-hinh' not in m_cats: continue

                # 2. Lọc Lẻ/Bộ
                if is_movie is True and not is_actually_movie: continue
                if is_movie is False and is_actually_movie: continue
                
                # 3. Lọc Quốc gia
                if country and country not in m_countries: continue
                
                # Nếu vượt qua hết thì hốt
                lang_raw = str(m.get('lang', ''))
                results.append({
                    "name": m.get('name'),
                    "year": int(m.get('year', 0)),
                    "slug": m.get('slug'),
                    "thumb": m.get('thumb_url'),
                    "poster": m.get('poster_url'),
                    "sub_type": "Lồng Tiếng" if "Lồng Tiếng" in lang_raw else ("Thuyết Minh" if "Thuyết Minh" in lang_raw else "Vietsub"),
                    "current_episode": m.get('episode_current', 'Full'),
                    "total_episodes": str(m.get('episode_total', '1')),
                    "country": m_countries[0] if m_countries else ""
                })
                seen.add(m.get('slug'))

            print(f"  + {display_name} ({year} - Trang {page}): Hiện có {len(results)} phim")
            time.sleep(0.1)

    # Xuất file riêng cho từng loại
    file_path = os.path.join(OUTPUT_DIR, f"{filename}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, separators=(',', ':'))
    return len(results)

def main():
    start_time = time.time()
    
    # Thứ tự chuẩn ní yêu cầu
    tasks = [
        ("Phim Chiếu Rạp", "phim_chieu_rap", "phim-chieu-rap"),
        ("Lồng Tiếng", "long_tieng", "phim-moi", None, None, None, False, "long-tieng"),
        ("Thuyết Minh", "thuyet_minh", "phim-moi", None, None, None, False, "thuyet-minh"),
        
        # Anime & Hoạt hình (is_anime=True)
        ("Anime Movie", "anime_movie", "hoat-hinh", None, True, None, True),
        ("Anime Nhật", "anime_nhat", "hoat-hinh", "Nhật Bản", False, None, True),
        ("HH Trung Quốc", "hh_trung_quoc", "hoat-hinh", "Trung Quốc", False, None, True),
        
        # Phim Lẻ (is_movie=True)
        ("Phim Lẻ Trung", "le_trung", "phim-le", "Trung Quốc", True),
        ("Phim Lẻ Hàn", "le_han", "phim-le", "Hàn Quốc", True),
        ("Phim Lẻ Âu Mỹ", "le_au_my", "phim-le", "Âu Mỹ", True),
        ("Phim Lẻ Việt", "le_viet", "phim-le", "Việt Nam", True),
        ("Phim Lẻ Thái", "le_thai", "phim-le", "Thái Lan", True),
        
        # Phim Bộ (is_movie=False)
        ("Phim Bộ Trung", "bo_trung", "phim-bo", "Trung Quốc", False),
        ("Phim Bộ Hàn", "bo_han", "phim-bo", "Hàn Quốc", False),
        ("Phim Bộ Âu Mỹ", "bo_au_my", "phim-bo", "Âu Mỹ", False),
        ("Phim Bộ Việt", "bo_viet", "phim-bo", "Việt Nam", False),
        ("Phim Bộ Thái", "bo_thai", "phim-bo", "Thái Lan", False),
        
        # Thể loại & Show
        ("Phim Kinh Dị", "kinh_di", "phim-moi", None, None, "kinh-di"),
        ("Phim Hài", "hai_huoc", "phim-moi", None, None, "hai-huoc"),
        ("Phim Cổ Trang", "co_trang", "phim-moi", None, None, "co-trang"),
        ("Phim Khoa Học", "khoa_hoc", "phim-moi", None, None, "khoa-hoc"),
        ("TV Show", "tv_show", "tv-shows")
    ]

    summary = []
    for task in tasks:
        # Giải nén tuple linh hoạt
        name, fname, endp = task[:3]
        country = task[3] if len(task) > 3 else None
        is_movie = task[4] if len(task) > 4 else None
        cat = task[5] if len(task) > 5 else None
        is_ani = task[6] if len(task) > 6 else False
        lang = task[7] if len(task) > 7 else None
        
        count = crawl_category(name, fname, endp, country, is_movie, cat, is_ani, lang)
        summary.append(f"| {name:20} | {count:10} |")

    print("\n" + "="*40)
    print("HOÀN THÀNH QUÁ TRÌNH TỔNG LỰC")
    for line in summary: print(line)
    print(f"Tổng thời gian: {int(time.time() - start_time)//60} phút")
    print(f"Dữ liệu nằm tại thư mục: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
