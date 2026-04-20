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
MAX_WORKERS = 2
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
    print(f"> Đang quét: {target_name}...")
    
    # Quét từ trang 1 đến 10 để lấy hàng mới nhất thay vì lọc theo năm
    for page in range(1, 11): 
        if len(results) >= TARGET_COUNT: break
        
        url = f"{BASE_URL}/danh-sach/{endpoint}"
        params = {"page": page, "limit": 64}
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
                    "year": int(m.get('year', 0)),
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
        time.sleep(0.3)
    return results

def fetch_by_lang(lang_code, lang_name):
    results = []
    local_seen = set()
    print(f"> Đang quét: Phim {lang_name} (Mới cập nhật)...")

    # Quét trực tiếp danh sách phim mới để lọc ngôn ngữ
    for page in range(1, 11):
        if len(results) >= TARGET_COUNT: break
        url = f"{BASE_URL}/danh-sach/phim-moi"
        params = {"page": page, "limit": 64}
        
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
            
            # Lọc đúng loại ngôn ngữ (long-tieng hoặc thuyet-minh)
            if (lang_code == "long-tieng" and "Lồng Tiếng" in lang) or \
               (lang_code == "thuyet-minh" and "Thuyết Minh" in lang):
                
                desc = m.get('content', '').replace('<p>', '').replace('</p>', '').replace('\n', ' ').strip()
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
                    "description": desc
                })
                local_seen.add(m.get('slug'))
        time.sleep(0.3)
    return results

def interleave_trending(tr, han, au, thai, rap):
    trending = []
    l_tr, l_han, l_au, l_thai, l_rap = list(tr[:4]), list(han[:3]), list(au[:3]), list(thai[:2]), list(rap[:3])
    while l_tr or l_han or l_au or l_thai or l_rap:
        if l_tr: trending.append(l_tr.pop(0))
        if l_rap: trending.append(l_rap.pop(0))
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

    # 1. Quét dữ liệu (Giữ nguyên Key cho Android Studio)
    run_and_report("anime_movie", "Anime Movie", "hoat-hinh", is_movie=True)
    run_and_report("anime_nhat", "Anime Nhật", "hoat-hinh", country="Nhật Bản", is_movie=False)
    run_and_report("hh_trung_quoc", "HH Trung Quốc", "hoat-hinh", country="Trung Quốc", is_movie=False)
    run_and_report("phim_chieu_rap", "Phim Chiếu Rạp", "phim-chieu-rap")

    mapping = [("Việt Nam", "vn"), ("Hàn Quốc", "han"), ("Trung Quốc", "trung"), ("Âu Mỹ", "au_my"), ("Thái Lan", "thai")]
    for c_name, c_key in mapping:
        run_and_report(f"le_{c_key}", f"Lẻ {c_name}", "phim-le", country=c_name, is_movie=True)
        run_and_report(f"bo_{c_key}", f"Bộ {c_name}", "phim-bo", country=c_name, is_movie=False)

    # 2. Trending
    final_data["trending_phim_bo"] = interleave_trending(
        final_data.get("bo_trung", []), final_data.get("bo_han", []),
        final_data.get("bo_au_my", []), final_data.get("bo_thai", []),
        final_data.get("phim_chieu_rap", [])
    )
    report.append(f"| {'Top Trending':22} | {'🔥 MIXED':16} |")

    # 3. Lồng Tiếng / Thuyết Minh
    final_data["long_tieng"] = fetch_by_lang("long-tieng", "Lồng Tiếng")
    final_data["thuyet_minh"] = fetch_by_lang("thuyet-minh", "Thuyết Minh")

    # 4. Lưu file JSON với Indent 4
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)

    # --- BẢNG THÔNG BÁO ---
    print("\n" + "="*45)
    print(f"    BÁO CÁO CRAWL - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("="*45)
    print(f"| {'Hạng mục':22} | {'Trạng thái':16} |")
    print("-" * 45)
    for line in report:
        print(line)
    print("="*45)
    print(f"Tổng thời gian: {int(time.time() - start_time)}s")
    print(f"File lưu tại: {DATA_FILE} (Indent=4)\n")

if __name__ == "__main__":
    main()
