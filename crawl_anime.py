import requests
import json
import time

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

def fetch_category(api_path, target_key, limit=15):
    results = []
    page = 1
    current_min_year = 2026
    
    print(f"\n--- Đang săn: {target_key} (Mục tiêu: {limit} phim {current_min_year}+) ---")
    
    while len(results) < limit:
        # Nếu quét quá 40 trang mà chưa đủ 15 phim, nới lỏng xuống năm 2025
        if page > 40 and current_min_year > 2025:
            current_min_year = 2025
            print(f"  (!) Hạ tiêu chuẩn xuống năm {current_min_year} để gom đủ số lượng...")

        url = f"https://phimapi.com/v1/api/{api_path}?page={page}"
        data = get_data(url)
        
        if not data or 'data' not in data or not data['data'].get('items'):
            print(f"  (!) Hết kho phim tại trang {page}. Dừng với {len(results)} phim.")
            break
            
        for item in data['data']['items']:
            if len(results) >= limit: break
            
            detail = get_data(f"https://phimapi.com/phim/{item['slug']}")
            if not detail or 'movie' not in detail: continue
            
            m = detail['movie']
            year = int(m.get('year', 0))
            if year < current_min_year: continue

            # Chuẩn hóa sub_type
            lang = m.get('lang', 'Vietsub')
            sub_display = "Vietsub"
            if "Lồng Tiếng" in lang: sub_display = "Lồng Tiếng"
            elif "Thuyết Minh" in lang: sub_display = "Thuyết Minh"

            info = {
                "name": m.get('name'), 
                "year": year, 
                "thumb": m.get('thumb_url'), 
                "poster": m.get('poster_url'),
                "slug": item['slug'],
                "sub_type": sub_display,
                "current_episode": m.get('episode_current', '0'),
                "total_episodes": m.get('episode_total', '??'),
                "country": m.get('country', [{}])[0].get('name', ''),
                "type": m.get('type', '')
            }
            
            if not any(x['slug'] == info['slug'] for x in results):
                results.append(info)
                print(f"  [+] {target_key}: {info['name']} ({year})")
            
            time.sleep(0.7)
        page += 1
    return results

def main():
    final_data = {}
    
    # 1. Cào các danh mục cơ bản (Mỗi loại 15 phim)
    categories = {
        "phim_moi": "danh-sach/phim-moi-cap-nhat",
        "phim_chieu_rap": "danh-sach/phim-dang-chieu",
        "anime_movie": "danh-sach/hoat-hinh", # Sẽ lọc lẻ ở bước hiển thị hoặc lấy 15 cái mới nhất
        "anime_nhat": "quoc-gia/nhat-ban",
        "hh_trung_quoc": "quoc-gia/trung-quoc", # Sẽ dùng chung API quốc gia rồi lọc type hoat-hinh nếu cần
        "phim_le": "danh-sach/phim-le",
        "le_viet_nam": "quoc-gia/viet-nam",
        "le_han_quoc": "quoc-gia/han-quoc",
        "le_trung_quoc": "quoc-gia/trung-quoc",
        "le_thai_lan": "quoc-gia/thai-lan",
        "le_au_my": "quoc-gia/au-my",
        "bo_viet_nam": "quoc-gia/viet-nam",
        "bo_han_quoc": "quoc-gia/han-quoc",
        "bo_trung_quoc": "quoc-gia/trung-quoc",
        "bo_thai_lan": "quoc-gia/thai-lan",
        "bo_au_my": "quoc-gia/au-my"
    }

    for key, path in categories.items():
        # Phân loại phim bộ/lẻ cho chính xác khi cào theo quốc gia
        raw_list = fetch_category(path, key, limit=15)
        if "le_" in key:
            final_data[key] = [x for x in raw_list if x['type'] == 'single'][:15]
        elif "bo_" in key:
            final_data[key] = [x for x in raw_list if x['type'] == 'series'][:15]
        else:
            final_data[key] = raw_list

    # 2. Tổng hợp Top 10 Phim Bộ (4 Trung, 3 Hàn, 2 Mỹ, 1 Thái)
    top_10 = []
    top_10.extend(final_data.get("bo_trung_quoc", [])[:4])
    top_10.extend(final_data.get("bo_han_quoc", [])[:3])
    top_10.extend(final_data.get("bo_au_my", [])[:2])
    top_10.extend(final_data.get("bo_thai_lan", [])[:1])
    final_data["top_10_series"] = top_10

    # 3. Tổng hợp Phim Lồng Tiếng & Thuyết Minh (Quét từ toàn bộ dữ liệu đã cào)
    all_movies = []
    for v in final_data.values(): all_movies.extend(v)
    
    final_data["phim_long_tieng"] = [m for m in all_movies if m['sub_type'] == "Lồng Tiếng"][:15]
    final_data["phim_thuyet_minh"] = [m for m in all_movies if m['sub_type'] == "Thuyết Minh"][:15]

    # Lưu file
    with open("data_2026_perfect.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    print("\n[XONG] Đã cập nhật toàn bộ 18 danh mục phim!")

if __name__ == "__main__":
    main()
