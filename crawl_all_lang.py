import requests
import json
import time
import random
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# --- CẤU HÌNH ---
BASE_URL = "https://phimapi.com/v1/api"
YEAR_RANGE = [2026, 2025, 2024] 
LIMIT_PER_SECTION = 400 # Số lượng ní muốn
MAX_WORKERS = 3
OUTPUT_FILE = "data_all_lang_library.json"

# Danh sách danh mục rút gọn
CATEGORIES = [
    {"name": "Kinh Dị", "slug": "kinh-di"},
    {"name": "Hài Hước", "slug": "hai-huoc"},
    {"name": "Hoạt Hình", "slug": "hoat-hinh"},
    {"name": "Chiếu Rạp", "slug": "phim-chieu-rap"}
]

COUNTRIES = [
    {"name": "Hàn Quốc", "slug": "han-quoc"},
    {"name": "Trung Quốc", "slug": "trung-quoc"},
    {"name": "Âu Mỹ", "slug": "au-my"},
    {"name": "Nhật Bản", "slug": "nhat-ban"},
    {"name": "Thái Lan", "slug": "thai-lan"},
    {"name": "Việt Nam", "slug": "viet-nam"}
]

def get_data(url, params=None):
    headers = {"User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(100, 115)}.0.0.0 Safari/537.36"}
    try:
        res = requests.get(url, params=params, timeout=25)
        if res.status_code == 200: return res.json()
    except: pass
    return None

def fetch_detail(slug):
    time.sleep(0.1) # Nghỉ nhẹ tránh bị block
    return get_data(f"https://phimapi.com/phim/{slug}")

def crawl_by_filter(filter_type, slug, display_name):
    results = []
    seen = set()
    print(f"\n> Đang hốt mục: {display_name}...")

    for year in YEAR_RANGE:
        if len(results) >= LIMIT_PER_SECTION: break
        
        # Quét sâu 5 trang để lấy đủ số lượng
        for page in range(1, 6):
            if len(results) >= LIMIT_PER_SECTION: break
            
            # Logic Endpoint đặc biệt
            if slug in ['hoat-hinh', 'phim-chieu-rap', 'phim-bo']:
                url = f"{BASE_URL}/danh-sach/{slug}"
                params = {"year": year, "page": page, "limit": 64}
            else:
                url = f"{BASE_URL}/nam/{year}"
                params = {"page": page, "limit": 64, "sort_field": "modified.time", "sort_type": "desc"}
                if filter_type == 'the-loai': params['category'] = slug
                if filter_type == 'quoc-gia': params['country'] = slug
                if filter_type == 'lang': params['sort_lang'] = slug

            data = get_data(url, params)
            if not data or 'data' not in data or not data['data'].get('items'):
                break 
                
            items = data['data']['items']
            slugs_to_fetch = [it['slug'] for it in items if it['slug'] not in seen]
            
            if not slugs_to_fetch: continue

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                details = list(executor.map(fetch_detail, slugs_to_fetch))

            for detail in details:
                if len(results) >= LIMIT_PER_SECTION: break
                if not detail or 'movie' not in detail: continue
                m = detail['movie']
                
                # Xác định nhãn sub_type hiển thị trên App
                if filter_type == 'lang':
                    sub_val = display_name
                else:
                    lang_raw = str(m.get('lang', '')).lower()
                    if "lồng tiếng" in lang_raw: sub_val = "Lồng Tiếng"
                    elif "thuyết minh" in lang_raw: sub_val = "Thuyết Minh"
                    else: sub_val = "Vietsub"

                results.append({
                    "name": m.get('name'),
                    "year": m.get('year'),
                    "slug": m.get('slug'),
                    "thumb": m.get('thumb_url'),
                    "poster": m.get('poster_url'),
                    "sub_type": sub_val,
                    "current_episode": m.get('episode_current', 'Full'),
                    "total_episodes": str(m.get('episode_total', '1')),
                    "country": m.get('country', [{}])[0].get('name', '')
                })
                seen.add(m.get('slug'))
            
            print(f"  + {display_name} {year} (Trang {page}): Lấy thêm {len(slugs_to_fetch)} phim")
            time.sleep(random.uniform(1, 2))
            
    return results

def main():
    start_time = time.time()
    final_library = {
        "all_long_tieng": [],
        "all_thuyet_minh": [],
        "phim_bo": [],
        "the_loai": {},
        "quoc_gia": {}
    }
    report = []

    # 1. Lồng Tiếng & Thuyết Minh
    lt = crawl_by_filter('lang', 'long-tieng', 'Lồng Tiếng')
    final_library["all_long_tieng"] = lt
    report.append(f"| {'Lồng Tiếng':22} | {len(lt):16} |")

    tm = crawl_by_filter('lang', 'thuyet-minh', 'Thuyết Minh')
    final_library["all_thuyet_minh"] = tm
    report.append(f"| {'Thuyết Minh':22} | {len(tm):16} |")

    # 2. Phim Bộ
    pb = crawl_by_filter('the-loai', 'phim-bo', 'Phim Bộ')
    final_library["phim_bo"] = pb
    report.append(f"| {'Phim Bộ':22} | {len(pb):16} |")

    # 3. Thể Loại
    for cat in CATEGORIES:
        res = crawl_by_filter('the-loai', cat['slug'], cat['name'])
        final_library["the_loai"][cat['slug']] = res
        report.append(f"| {cat['name']:22} | {len(res):16} |")

    # 4. Quốc Gia
    for cou in COUNTRIES:
        res = crawl_by_filter('quoc-gia', cou['slug'], cou['name'])
        final_library["quoc_gia"][cou['slug']] = res
        report.append(f"| {cou['name']:22} | {len(res):16} |")

    # Lưu file kiểu nén (Minify) để giảm dung lượng nhưng giữ nguyên tên Key
    print(f"\n[Hệ thống] Đang ghi file {OUTPUT_FILE} (Bản tối ưu dung lượng)...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        # Bỏ indent=4, thêm separators để xóa khoảng trắng thừa
        json.dump(final_library, f, ensure_ascii=False, separators=(',', ':'))

    # In báo cáo cuối cùng
    print("\n" + "="*45)
    print(f"   BÁO CÁO KHO TỔNG HỢP - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("="*45)
    print(f"| {'Hạng mục':22} | {'Số lượng':16} |")
    print("-" * 45)
    for line in report:
        print(line)
    print("="*45)
    print(f"Hoàn thành trong: {int(time.time() - start_time)//60} phút.\n")

if __name__ == "__main__":
    main()
