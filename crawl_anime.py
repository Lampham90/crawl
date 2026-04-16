import requests
import json
import os
import time

MAX_WORKERS = 10
def get_data(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        res = requests.get(url, headers=headers, timeout=20)
        if res.status_code == 200:
            d = res.json()
            return d if isinstance(d, dict) else None
        return None
    except:
        return None

def fetch_until_full_v12(api_type, target_key):
    results = []
    page = 1
    current_min_year = 2026
    
    print(f"\n--- Đang săn tìm: {target_key} (Mục tiêu: 10 phim {current_min_year}+) ---")
    
    while len(results) < 10:
        if page > 30 and current_min_year > 2025:
            current_min_year = 2025
            print(f"  (!) Nới lỏng tiêu chuẩn xuống năm {current_min_year}...")

        url = f"https://phimapi.com/v1/api/danh-sach/{api_type}?page={page}"
        if "quoc-gia" in api_type:
            url = f"https://phimapi.com/v1/api/{api_type}?page={page}"
            
        data = get_data(url)
        if not data or 'data' not in data or not data['data'].get('items'):
            print(f"  (!) Đã quét hết kho phim tại trang {page}. Dừng lại với {len(results)} phim.")
            break
            
        items = data['data']['items']
        for item in items:
            if len(results) >= 10: break
            
            detail = get_data(f"https://phimapi.com/phim/{item['slug']}")
            if not detail or 'movie' not in detail: continue
            
            m = detail['movie']
            year = int(m.get('year', 0))
            
            if year < current_min_year:
                continue 

            ep_total = str(m.get('episode_total', ''))
            status = str(m.get('episode_current', '')).lower()
            country = m.get('country', [{}])[0].get('name', '')
            
            # --- Logic chuẩn hóa Thuyết minh/Lồng tiếng ---
            original_lang = m.get('lang', 'Vietsub')
            if "Lồng Tiếng" in original_lang:
                sub_display = "Lồng Tiếng"
            elif "Thuyết Minh" in original_lang:
                sub_display = "Thuyết Minh"
            else:
                sub_display = "Vietsub" 

            info = {
                "name": m.get('name'), 
                "year": year, 
                "thumb": m.get('thumb_url'), 
                "slug": item['slug'], # Thêm dấu phẩy ở đây
                "sub_type": sub_display, # Sử dụng sub_display đã chuẩn hóa
                "current_episode": m.get('episode_current', '0'),
                "total_episodes": m.get('episode_total', '??')
            }
            
            if any(x['slug'] == item['slug'] for x in results):
                continue

            if target_key == "anime_movie":
                if ep_total == "1" or "full" in status: 
                    results.append(info)
                    print(f"  [+] Movie 2026: {info['name']}")
            elif target_key == "anime_nhat":
                if country == "Nhật Bản" and ep_total != "1": 
                    results.append(info)
                    print(f"  [+] Anime Nhật 2026: {info['name']}")
            elif target_key == "hh_trung_quoc":
                if country == "Trung Quốc" and ep_total != "1": 
                    results.append(info)
                    print(f"  [+] HH Trung 2026: {info['name']}")
            elif target_key == "phim_le_han":
                if ep_total == "1" or "full" in status: 
                    results.append(info)
                    print(f"  [+] Hàn lẻ 2026: {info['name']}")
            elif target_key == "phim_le_trung":
                if ep_total == "1" or "full" in status: 
                    results.append(info)
                    print(f"  [+] Trung lẻ 2026: {info['name']}")
                
            time.sleep(0.7) 
        
        page += 1
        
    return results

def main_v12():
    final_data = {}
    
    final_data["anime_nhat"] = fetch_until_full_v12("hoat-hinh", "anime_nhat")
    final_data["hh_trung_quoc"] = fetch_until_full_v12("hoat-hinh", "hh_trung_quoc")
    final_data["anime_movie"] = fetch_until_full_v12("hoat-hinh", "anime_movie")
    final_data["han_quoc_le"] = fetch_until_full_v12("quoc-gia/han-quoc", "phim_le_han")
    final_data["trung_quoc_le"] = fetch_until_full_v12("quoc-gia/trung-quoc", "phim_le_trung")

    for k in final_data:
        final_data[k] = sorted(final_data[k], key=lambda x: x.get('year', 0), reverse=True)

    path = "data_2026_perfect.json" 
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    
    print(f"\n[XONG] Script đã hoàn tất. Dữ liệu đã được lưu vào: {path}")

if __name__ == "__main__":
    main_v12()
