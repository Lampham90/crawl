import requests
import json
import time
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# --- CẤU HÌNH ---
BASE_URL = "https://phimapi.com/v1/api"
YEARS = [2026, 2025, 2024, 2023, 2022] 
LIMIT_COUNT = 200
MAX_WORKERS = 2
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

# --- LOGIC 1: ĐÁNH THẲNG Ổ HOẠT HÌNH (ANIME) ---
def crawl_hoat_hinh(display_name, filename, country=None, is_movie=None):
    results = []
    seen = set()
    print(f"\n>>> Đang hốt {display_name} (Chuyên biệt Hoạt Hình)...")
    
    for page in range(1, 40): # Quét cực sâu để đủ 200 phim đặc thù
        if len(results) >= LIMIT_COUNT: break
        data = get_data(f"{BASE_URL}/danh-sach/hoat-hinh", {"page": page, "limit": 64})
        if not data or 'data' not in data: break
        
        items = data['data']['items']
        slugs = [it['slug'] for it in items if it['slug'] not in seen]
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            details = list(executor.map(fetch_detail, slugs))

        for d in details:
            if len(results) >= LIMIT_COUNT: break
            if not d or 'movie' not in d: continue
            m = d['movie']
            
            m_countries = [c.get('name') for c in m.get('country', [])]
            is_actually_movie = (m.get('type') == 'single' or str(m.get('episode_total')) == "1")

            if country and country not in m_countries: continue
            if is_movie is True and not is_actually_movie: continue
            if is_movie is False and is_actually_movie: continue

            results.append({
                "name": m.get('name'),
                "year": int(m.get('year', 0)),
                "slug": m.get('slug'),
                "thumb": m.get('thumb_url'),
                "poster": m.get('poster_url'),
                "sub_type": "Lồng Tiếng" if "Lồng Tiếng" in str(m.get('lang','')) else "Thuyết Minh",
                "current_episode": m.get('episode_current', 'Full'),
                "total_episodes": str(m.get('episode_total', '1')),
                "country": m_countries[0] if m_countries else ""
            })
            seen.add(m['slug'])
    
    save_file(filename, results)
    return len(results)

# --- LOGIC 2: QUÉT PHIM LẺ, BỘ, THỂ LOẠI (LOẠI TRỪ HOẠT HÌNH) ---
def crawl_general(display_name, filename, endpoint, country=None, is_movie=None, category=None, lang_key=None):
    results = []
    seen = set()
    print(f"\n>>> Đang đào mục: {display_name}...")

    for year in YEARS:
        if len(results) >= LIMIT_COUNT: break
        
        # Chọn endpoint
        if endpoint in ['phim-chieu-rap', 'phim-le', 'phim-bo', 'tv-shows']:
            url = f"{BASE_URL}/danh-sach/{endpoint}"
            params = {"year": year, "page": 1, "limit": 64}
        else:
            url = f"{BASE_URL}/nam/{year}"
            params = {"page": 1, "limit": 64, "sort_field": "modified.time"}
            if category: params['category'] = category
            if lang_key: params['sort_lang'] = lang_key

        for page in range(1, 15):
            if len(results) >= LIMIT_COUNT: break
            params['page'] = page
            data = get_data(url, params)
            if not data or 'data' not in data or not data['data'].get('items'): break
            
            items = data['data']['items']
            slugs = [it['slug'] for it in items if it['slug'] not in seen]
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                details = list(executor.map(fetch_detail, slugs))

            for detail in details:
                if len(results) >= LIMIT_COUNT: break
                if not detail or 'movie' not in detail: continue
                m = detail['movie']
                
                # Loại trừ Hoạt hình ra khỏi các mục phim người đóng
                m_cats = [c.get('slug') for c in m.get('category', [])]
                if 'hoat-hinh' in m_cats: continue

                m_countries = [c.get('name') for c in m.get('country', [])]
                is_actually_movie = (m.get('type') == 'single' or str(m.get('episode_total')) == "1")

                if country and country not in m_countries: continue
                if is_movie is True and not is_actually_movie: continue
                if is_movie is False and is_actually_movie: continue

                results.append({
                    "name": m.get('name'),
                    "year": int(m.get('year', 0)),
                    "slug": m.get('slug'),
                    "thumb": m.get('thumb_url'),
                    "poster": m.get('poster_url'),
                    "sub_type": "Lồng Tiếng" if "Lồng Tiếng" in str(m.get('lang','')) else "Thuyết Minh",
                    "current_episode": m.get('episode_current', 'Full'),
                    "total_episodes": str(m.get('episode_total', '1')),
                    "country": m_countries[0] if m_countries else ""
                })
                seen.add(m['slug'])
            time.sleep(0.1)

    save_file(filename, results)
    return len(results)

def save_file(filename, data):
    with open(os.path.join(OUTPUT_DIR, f"{filename}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

def main():
    start_time = time.time()
    summary = []

    # 1. Chiếu rạp, Lồng tiếng, Thuyết minh
    summary.append(f"Rạp: {crawl_general('Phim Rạp', 'phim_chieu_rap', 'phim-chieu-rap')}")
    summary.append(f"LT: {crawl_general('Lồng Tiếng', 'long_tieng', 'phim-moi', lang_key='long-tieng')}")
    summary.append(f"TM: {crawl_general('Thuyết Minh', 'thuyet_minh', 'phim-moi', lang_key='thuyet-minh')}")

    # 2. Hoạt hình (Logic đánh thẳng ổ)
    summary.append(f"Anime M: {crawl_hoat_hinh('Anime Movie', 'anime_movie', is_movie=True)}")
    summary.append(f"Anime N: {crawl_hoat_hinh('Anime Nhật', 'anime_nhat', country='Nhật Bản', is_movie=False)}")
    summary.append(f"HH Trung: {crawl_hoat_hinh('HH Trung Quốc', 'hh_trung_quoc', country='Trung Quốc', is_movie=False)}")

    # 3. Phim Lẻ các nước
    mapping_le = [("Việt Nam", "le_viet"), ("Hàn Quốc", "le_han"), ("Trung Quốc", "le_trung"), ("Âu Mỹ", "le_au_my"), ("Thái Lan", "le_thai")]
    for c_name, f_name in mapping_le:
        summary.append(f"{f_name}: {crawl_general(f'Lẻ {c_name}', f_name, 'phim-le', country=c_name, is_movie=True)}")

    # 4. Phim Bộ các nước
    mapping_bo = [("Việt Nam", "bo_viet"), ("Hàn Quốc", "bo_han"), ("Trung Quốc", "bo_trung"), ("Âu Mỹ", "bo_au_my"), ("Thái Lan", "bo_thai")]
    for c_name, f_name in mapping_bo:
        summary.append(f"{f_name}: {crawl_general(f'Bộ {c_name}', f_name, 'phim-bo', country=c_name, is_movie=False)}")

    # 5. Thể loại & TV Show
    summary.append(f"Kinh dị: {crawl_general('Kinh Dị', 'kinh_di', 'phim-moi', category='kinh-di')}")
    summary.append(f"Hài: {crawl_general('Hài', 'hai_huoc', 'phim-moi', category='hai-huoc')}")
    summary.append(f"Cổ trang: {crawl_general('Cổ Trang', 'co_trang', 'phim-moi', category='co-trang')}")
    summary.append(f"Khoa học: {crawl_general('Khoa Học', 'khoa_hoc', 'phim-moi', category='khoa-hoc')}")
    summary.append(f"TV Show: {crawl_general('TV Show', 'tv_show', 'tv-shows')}")

    print("\n" + "="*30)
    print("HOÀN THÀNH CRAWL CATALOG")
    for s in summary: print(s)
    print(f"Time: {int(time.time() - start_time)}s")

if __name__ == "__main__":
    main()
