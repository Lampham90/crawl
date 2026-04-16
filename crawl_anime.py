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
    # Lấy chi tiết để lọc chính xác quốc gia và năm
    detail = get_data(f"https://phimapi.com/phim/{item['slug']}")
    if not detail or 'movie' not in detail: 
        return None
        
    m = detail['movie']
    year = int(m.get('year', 0))
    if year < current_min_year:
        return None

    # Chuẩn hóa tên quốc gia
    countries = [str(c.get('name', '')).strip() for c in m.get('country', [])]
    
    # Logic phân loại Lẻ/Bộ dựa trên type của API
    m_type = m.get('type', '') # 'single' hoặc 'series'
    ep_current = str(m.get('episode_current', '')).lower()
    
    # Gán nhãn sub
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
    # --- LOGIC LỌC CHUẨN ---
    if target_key == "anime_movie":
        if m_type == 'single' or "hoạt hình" in str(m.get('category')).lower(): valid = True
    elif target_key == "anime_nhat":
        if "Nhật Bản" in countries and m_type == 'series': valid = True
    elif target_key == "hh_trung_quoc":
        if "Trung Quốc" in countries and m_type == 'series': valid = True
    elif target_key == "phim_le_han":
        if "Hàn Quốc" in countries and m_type == 'single': valid = True
    elif target_key == "phim_le_trung":
        if "Trung Quốc" in countries and m_type == 'single': valid = True
    elif target_key == "phim_le_vn":
        if "Việt Nam" in countries and m_type == 'single': valid = True
    elif target_key == "phim_le_thai":
        if "Thái Lan" in countries and m_type == 'single': valid = True
    elif target_key == "phim_bo_han":
        if "Hàn Quốc" in countries and m_type == 'series': valid = True
    elif target_key == "phim_bo_trung":
        if "Trung Quốc" in countries and m_type == 'series': valid = True
    elif target_key == "phim_bo_thai":
        if "Thái Lan" in countries and m_type == 'series': valid = True
    elif target_key == "phim_bo_aumy":
        aumy_keywords = ["Mỹ", "Âu Mỹ", "Anh", "Pháp", "Đức"]
        if any(c in aumy_keywords for c in countries) and m_type == 'series': valid = True
    
    return info if valid else None

def fetch_until_full_v12(api_type, target_key):
    results = []
    page = 1
    current_min_year = 2026
    
    print(f"\n--- Đang săn tìm: {target_key} ---")
    
    while len(results) < 10:
        if page > 25 and current_min_year > 2025:
            current_min_year = 2025
            print(f"  (!) Hạ tiêu chuẩn xuống {current_min_year}")

        # SỬ DỤNG ENDPOINT V1 CHUẨN
        url = f"https://phimapi.com/v1/api/danh-sach/{api_type}?page={page}"
            
        data = get_data(url)
        if not data or 'data' not in data or not data['data'].get('items'):
            break
            
        items = data['data']['items']
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_item = {executor.submit(process_item, item, target_key, current_min_year): item for item in items}
            for future in as_completed(future_to_item):
                if len(results) >= 10: break
                res = future.result()
                if res and not any(x['slug'] == res['slug'] for x in results):
                    results.append(res)
                    print(f"  [+] {res['name']} ({res['year']})")
        
        page += 1
        if page > 80: break 
        
    return results

def main_v12():
    final_data = {}
    
    # Cấu hình quét theo LOẠI PHIM (Lẻ/Bộ/Hoạt hình) để không bị sót
    # Cấu trúc: (Endpoint API, Target_Key nội bộ, Key lưu JSON)
    configs = [
        ("hoat-hinh", "anime_nhat", "anime_nhat"),
        ("hoat-hinh", "hh_trung_quoc", "hh_trung_quoc"),
        ("hoat-hinh", "anime_movie", "anime_movie"),
        ("phim-le", "phim_le_han", "han_quoc_le"),
        ("phim-le", "phim_le_trung", "trung_quoc_le"),
        ("phim-le", "phim_le_vn", "viet_nam_le"),
        ("phim-le", "phim_le_thai", "thai_lan_le"),
        ("phim-bo", "phim_bo_han", "han_quoc_bo"),
        ("phim-bo", "phim_bo_trung", "trung_quoc_bo"),
        ("phim-bo", "phim_bo_thai", "thai_lan_bo"),
        ("phim-bo", "phim_bo_aumy", "au_my_bo"),
    ]

    for api, target, key in configs:
        final_data[key] = fetch_until_full_v12(api, target)

    # Sắp xếp và lưu
    path = "data_2026_perfect.json" 
    with open(path, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    print(f"\n[XONG] Đã quét đủ các mục. File: {path}")

if __name__ == "__main__":
    main_v12()
