import requests
import json
import time
import os
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

# --- CẤU HÌNH ---
BASE_URL = "https://phimapi.com/v1/api"
YEARS = [2026, 2025, 2024] 
TARGET_COUNT = 15
MAX_WORKERS = 5
DATA_FILE = "data_2026_perfect.json"
TIME_FILE = "last_run.txt"

def get_data(url, params=None):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
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
    print(f"> Đang quét: {target_name}...")
    
    for year in YEARS:
        if len(results) >= TARGET_COUNT: break
        max_pages = 15 if year == 2026 else 5
        
        for page in range(1, max_pages + 1): 
            if len(results) >= TARGET_COUNT: break
            url = f"{BASE_URL}/danh-sach/{endpoint}"
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

# MỚI: Hàm lấy phim theo ngôn ngữ dùng API /nam/
def fetch_by_lang(lang_code, lang_name):
    results = []
    local_seen = set()
    print(f"> Đang quét: Phim {lang_name} (API lọc theo năm)...")

    for year in YEARS:
        if len(results) >= TARGET_COUNT: break
        url = f"{BASE_URL}/nam/{year}"
        params = {"page": 1, "sort_field": "modified.time", "sort_type": "desc", "sort_lang": lang_code, "limit": 64}
        
        data = get_data(url, params)
        if not data or 'data' not in data or not data['data'].get('items'): continue
            
        items = data['data']['items']
        slugs_to_fetch = [it['slug'] for it in items if it['slug'] not in local_seen]
        if not slugs_to_fetch: continue

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            details = list(executor.map(fetch_detail, slugs_to_fetch))

        for detail in details:
            if len(results) >= TARGET_COUNT: break
            if not detail or 'movie' not in detail: continue
            m = detail['movie']
            lang = str(m.get('lang', ''))
            results.append({
                "name": m.get('name'),
                "year": int(m.get('year', 0)),
                "slug": m.get('slug'),
                "thumb": m.get('thumb_url'),
                "poster": m.get('poster_url'),
                "sub_type": lang_name,
                "current_episode": m.get('episode_current', 'Full'),
                "total_episodes": str(m.get('episode_total', '1')),
                "country": m.get('country', [{}])[0].get('name', ''),
                "lang_raw": lang
            })
            local_seen.add(m.get('slug'))
        time.sleep(0.3)
    return results

def interleave_trending(tr, han, au, thai):
    trending = []
    l_tr, l_han, l_au, l_thai = list(tr[:5]), list(han[:4]), list(au[:3]), list(thai[:3])
    while l_tr or l_han or l_au or l_thai:
        if l_tr: trending.append(l_tr.pop(0))
        if l_han: trending.append(l_han.pop(0))
        if l_au: trending.append(l_au.pop(0))
        if l_thai: trending.append(l_thai.pop(0))
    random.shuffle(trending)
    return trending[:15]

def main():
    start_time = time.time()
    final_data = {}
    report = []

    def run_and_report(key, name, endpoint, country=None, is_movie=None):
        res = fetch_final(name, endpoint, country, is_movie)
        final_data[key] = res
        status = "✅ ĐỦ" if len(res) >= TARGET_COUNT else f"⚠️ THIẾU ({len(res)}/{TARGET_COUNT})"
        report.append(f"| {name:22} | {status:16} |")
        return res

    # 1. Quét các mục chính
    run_and_report("anime_movie", "Anime Movie", "hoat-hinh", is_movie=True)
    run_and_report("anime_nhat", "Anime Nhật", "hoat-hinh", country="Nhật Bản", is_movie=False)
    run_and_report("hh_trung_quoc", "HH Trung Quốc", "hoat-hinh", country="Trung Quốc", is_movie=False)

    mapping = [("Việt Nam", "vn"), ("Hàn Quốc", "han"), ("Trung Quốc", "trung"), ("Âu Mỹ", "au_my"), ("Thái Lan", "thai")]
    for c_name, c_key in mapping:
        run_and_report(f"le_{c_key}", f"Lẻ {c_name}", "phim-le", country=c_name, is_movie=True)
        run_and_report(f"bo_{c_key}", f"Bộ {c_name}", "phim-bo", country=c_name, is_movie=False)

    # 2. Xử lý logic Trending 3 ngày/lần
    should_update_trending = True
    if os.path.exists(TIME_FILE):
        with open(TIME_FILE, "r") as f:
            try:
                last_date = datetime.strptime(f.read().strip(), "%Y-%m-%d")
                if datetime.now() < last_date + timedelta(days=3):
                    should_update_trending = False
            except: pass

    old_data = {}
    if not should_update_trending and os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try: old_data = json.load(f)
            except: pass

    if should_update_trending:
        print("\n[Hệ thống] Đang làm mới Trending...")
        final_data["trending_phim_bo"] = interleave_trending(
            final_data.get("bo_trung", []), final_data.get("bo_han", []),
            final_data.get("bo_au_my", []), final_data.get("bo_thai", [])
        )
        with open(TIME_FILE, "w") as f:
            f.write(datetime.now().strftime("%Y-%m-%d"))
        report.append(f"| {'Top Phim Bộ':22} | {'🔥 MỚI':16} |")
    else:
        print("\n[Hệ thống] Giữ Trending cũ.")
        final_data["trending_phim_bo"] = old_data.get("trending_phim_bo", [])
        report.append(f"| {'Top Phim Bộ':22} | {'♻️ CŨ':16} |")

    # 3. Lọc Lồng Tiếng / Thuyết Minh bằng API chuẩn
    final_data["long_tieng"] = fetch_by_lang("long-tieng", "Lồng Tiếng")
    final_data["thuyet_minh"] = fetch_by_lang("thuyet-minh", "Thuyết Minh")
    
    report.append(f"| {'Lồng Tiếng':22} | {('✅ ĐỦ' if len(final_data['long_tieng'])>=TARGET_COUNT else '⚠️ THIẾU'):16} |")
    report.append(f"| {'Thuyết Minh':22} | {('✅ ĐỦ' if len(final_data['thuyet_minh'])>=TARGET_COUNT else '⚠️ THIẾU'):16} |")

    # 4. Lưu file JSON
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)

    # 5. IN BÁO CÁO CUỐI CÙNG
    print("\n" + "="*45)
    print(f"   BÁO CÁO CRAWL - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("="*45)
    print(f"| {'Hạng mục':22} | {'Trạng thái':16} |")
    print("-" * 45)
    for line in report:
        print(line)
    print("="*45)
    print(f"Tổng thời gian: {int(time.time() - start_time)}s\n")

if __name__ == "__main__":
    main()
