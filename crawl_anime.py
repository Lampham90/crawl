import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

MAX_WORKERS = 10 

def get_data(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            d = res.json()
            return d if isinstance(d, dict) else None
        return None
    except:
        return None

def process_item(item, target_key, current_min_year):
    detail = get_data(f"https://phimapi.com/phim/{item['slug']}")
    if not detail or 'movie' not in detail: 
        return None
        
    m = detail['movie']
    year = int(m.get('year', 0))
    if year < current_min_year:
        return None

    # Lấy danh sách quốc gia và chuẩn hóa (xóa khoảng trắng thừa)
    countries = [str(c.get('name', '')).strip() for c in m.get('country', [])]
    
    ep_total = str(m.get('episode_total', ''))
    status = str(m.get('episode_current', '')).lower()
    m_type = str(m.get('type', '')) # 'single' là phim lẻ, 'series' là phim bộ

    # Logic phân loại Lẻ/Bộ chuẩn hơn
    is_le = (m_type == 'single' or ep_total == "1" or "full" in status)
    is_bo = (m_type == 'series' or (ep_total != "1" and "full" not in status))

    original_lang = m.get('lang', 'Vietsub')
    sub_display = "Vietsub"
    if "Lồng Tiếng" in original_lang: sub_display = "Lồng Tiếng"
    elif "Thuyết Minh" in original_lang: sub_display = "Thuyết Minh"

    info = {
        "name": m.get('name'), 
        "year": year, 
        "thumb": m.get('thumb_url'),
        "poster": m.get('poster_url'),
        "slug": item['slug'],
        "sub_type": sub_display,
        "current_episode": m.get('episode_current', '0'),
        "total_episodes": m.get('episode_total', '??')
    }

    valid = False
    # --- FIX LOGIC SO SÁNH ---
    if target_key == "anime_movie":
        if is_le: valid = True
    elif target_key == "anime_nhat":
        if "Nhật Bản" in countries and is_bo: valid = True
    elif target_key == "hh_trung_quoc":
        if "Trung Quốc" in countries and is_bo: valid = True
    elif target_key == "phim_le_han":
        if "Hàn Quốc" in countries and is_le: valid = True
    elif target_key == "phim_le_trung":
        if "Trung Quốc" in countries and is_le: valid = True
    elif target_key == "phim_le_vn":
        if "Việt Nam" in countries and is_le: valid = True
    elif target_key == "phim_le_thai":
        if "Thái Lan" in countries and is_le: valid = True
    elif target_key == "phim_bo_han":
        if "Hàn Quốc" in countries and is_bo: valid = True
    elif target_key == "phim_bo_trung":
        if "Trung Quốc" in countries and is_bo: valid = True
    elif target_key == "phim_bo_thai":
        if "Thái Lan" in countries and is_bo: valid = True
    elif target_key == "phim_bo_aumy":
        # Âu Mỹ thường gồm nhiều nước nhỏ, kiểm tra tập hợp
        aumy_list = ["Âu Mỹ", "Mỹ", "Anh", "Pháp", "Đức", "Canada"]
        if any(c in aumy_list for c in countries) and is_bo: valid = True
    
    return info if valid else None

def fetch_until_full_v12(api_type, target_key):
    results = []
    page = 1
    current_min_year = 2026
    
    print(f"\n--- Đang săn tìm: {target_key} (Mục tiêu: 10 phim {current_min_year}+) ---")
    
    while len(results) < 10:
        if page > 30 and current_min_year > 2025:
            current_min_year = 2025
            print(f"  (!) Nới lỏng tiêu chuẩn xuống năm {current_min_year}...")

        # API endpoint linh hoạt hơn
        if "quoc-gia" in api_type:
            url = f"https://phimapi.com/v1/api/{api_type}?page={page}"
        else:
            url = f"https://phimapi.com/v1/api/danh-sach/{api_type}?page={page}"
            
        data = get_data(url)
        if not data or 'data' not in data or not data['data'].get('items'):
            print(f"  (!) Hết dữ liệu tại trang {page}")
            break
            
        items = data['data']['items']
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_item = {executor.submit(process_item, item, target_key, current_min_year): item for item in items}
            for future in as_completed(future_to_item):
                res = future.result()
                if res and len(results) < 10:
                    if not any(x['slug'] == res['slug'] for x in results):
                        results.append(res)
                        print(f"  [+] Lấy được: {res['name']} ({res['year']})")
        
        page += 1
        if page > 100: break # Tránh treo nếu không tìm đủ 10 phim
        
    return results

def main_v12():
    final_data = {}
    
    # Cấu hình chuẩn để gọi đúng API
    configs = [
        ("hoat-hinh", "anime_nhat", "anime_nhat"),
        ("hoat-hinh", "hh_trung_quoc", "hh_trung_quoc"),
        ("hoat-hinh", "anime_movie", "anime_movie"),
        ("quoc-gia/han-quoc", "phim_le_han", "han_quoc_le"),
        ("quoc-gia/trung-quoc", "phim_le_trung", "trung_quoc_le"),
        ("quoc-gia/viet-nam", "phim_le_vn", "viet_nam_le"),
        ("quoc-gia/thai-lan", "phim_le_thai", "thai_lan_le"),
        ("quoc-gia/han-quoc", "phim_bo_han", "han_quoc_bo"),
        ("quoc-gia/trung-quoc", "phim_bo_trung", "trung_quoc_bo"),
        ("quoc-gia/thai-lan", "phim_bo_thai", "thai_lan_bo"),
        ("quoc-gia/au-my", "phim_bo_aumy", "au_my_bo"),
    ]

    for api, target, key in configs:
        final_data[key] = fetch_until_full_v12(api, target)

    # Sắp xếp
    for k in final_data:
        final_data[k] = sorted(final_data[k], key=lambda x: x.get('year', 0), reverse=True)

    path = "data_2026_perfect.json" 
    with open(path, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    
    print(f"\n[XONG] File đã lưu: {path}")

if __name__ == "__main__":
    main_v12()
