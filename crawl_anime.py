import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Tăng lên 15-20 nếu mạng khỏe, nhưng 10 là mức an toàn để không bị khóa IP
MAX_WORKERS = 12 

def get_data(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            d = res.json()
            return d if isinstance(d, dict) else None
        return None
    except:
        return None

def process_item(item, target_key, current_min_year):
    """Hàm xử lý chi tiết từng phim (Giữ nguyên logic lọc gốc)"""
    detail = get_data(f"https://phimapi.com/phim/{item['slug']}")
    if not detail or 'movie' not in detail: return None
    
    m = detail['movie']
    year = int(m.get('year', 0))
    if year < current_min_year: return None

    ep_total = str(m.get('episode_total', ''))
    status = str(m.get('episode_current', '')).lower()
    country = m.get('country', [{}])[0].get('name', '')
    
    original_lang = m.get('lang', 'Vietsub')
    if "Lồng Tiếng" in original_lang: sub_display = "Lồng Tiếng"
    elif "Thuyết Minh" in original_lang: sub_display = "Thuyết Minh"
    else: sub_display = "Vietsub" 

    info = {
        "name": m.get('name'), "year": year, 
        "thumb": m.get('thumb_url'), "poster": m.get('poster_url'),
        "slug": item['slug'], "sub_type": sub_display,
        "current_episode": m.get('episode_current', '0'),
        "total_episodes": m.get('episode_total', '??')
    }

    # Bộ lọc chính xác của bạn
    valid = False
    if target_key == "anime_movie" and (ep_total == "1" or "full" in status): valid = True
    elif target_key == "anime_nhat" and (country == "Nhật Bản" and ep_total != "1"): valid = True
    elif target_key == "hh_trung_quoc" and (country == "Trung Quốc" and ep_total != "1"): valid = True
    elif target_key in ["phim_le_han", "phim_le_trung", "phim_le_vn", "phim_le_thai"] and (ep_total == "1" or "full" in status): valid = True
    elif target_key in ["phim_bo_han", "phim_bo_trung", "phim_bo_thai", "phim_bo_aumy"] and (ep_total != "1" and "full" not in status): valid = True

    return info if valid else None

def fetch_category(config):
    """Hàm chạy cho từng hạng mục riêng biệt"""
    api_type, target_key, display_name = config
    results = []
    page = 1
    current_min_year = 2026
    
    print(f"[*] Bắt đầu quét: {display_name}")
    
    while len(results) < 10 and page <= 60:
        if page > 25: current_min_year = 2025
        
        url = f"https://phimapi.com/v1/api/danh-sach/{api_type}?page={page}"
        if "quoc-gia" in api_type:
            url = f"https://phimapi.com/v1/api/{api_type}?page={page}"
            
        data = get_data(url)
        if not data or 'data' not in data or not data['data'].get('items'): break
            
        items = data['data']['items']
        # Song song hóa việc lấy detail phim trong trang
        with ThreadPoolExecutor(max_workers=5) as item_executor:
            futures = [item_executor.submit(process_item, it, target_key, current_min_year) for it in items]
            for f in as_completed(futures):
                res = f.result()
                if res and len(results) < 10:
                    if not any(x['slug'] == res['slug'] for x in results):
                        results.append(res)

        page += 1
    print(f"[OK] Hoàn tất {display_name}: {len(results)} phim")
    return display_name, results

def main_v12():
    start_time = time.time()
    # Danh sách các luồng công việc
    configs = [
        ("hoat-hinh", "anime_nhat", "anime_nhat"),
        ("hoat-hinh", "hh_trung_quoc", "hh_trung_quoc"),
        ("hoat-hinh", "hoat-hinh", "anime_movie"),
        ("quoc-gia/han-quoc", "phim_le_han", "han_quoc_le"),
        ("quoc-gia/trung-quoc", "phim_le_trung", "trung_quoc_le"),
        ("quoc-gia/viet-nam", "phim_le_vn", "viet_nam_le"),
        ("quoc-gia/thai-lan", "phim_le_thai", "thai_lan_le"),
        ("quoc-gia/han-quoc", "phim_bo_han", "han_quoc_bo"),
        ("quoc-gia/trung-quoc", "phim_bo_trung", "trung_quoc_bo"),
        ("quoc-gia/thai-lan", "phim_bo_thai", "thai_lan_bo"),
        ("quoc-gia/au-my", "phim_bo_aumy", "au_my_bo")
    ]

    final_data = {}
    
    # Kỹ thuật "Double Parallel": Chạy song song cả các Hạng mục
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as category_executor:
        future_to_cat = {category_executor.submit(fetch_category, cfg): cfg for cfg in configs}
        for future in as_completed(future_to_cat):
            key, data = future.result()
            final_data[key] = sorted(data, key=lambda x: x.get('year', 0), reverse=True)

    with open("data_2026_perfect.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    
    end_time = time.time()
    print(f"\n[XONG] Tổng thời gian thực hiện: {round(end_time - start_time, 2)} giây.")

if __name__ == "__main__":
    main_v12()
