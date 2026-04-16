import requests
import json
import time

# Cấu hình chuẩn theo tài liệu [cite: 25, 42]
BASE_URL = "https://phimapi.com/v1/api"
TARGET_COUNT = 15
YEARS = [2026, 2025]

def get_data(url, params=None):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        res = requests.get(url, params=params, headers=headers, timeout=15)
        if res.status_code == 200:
            d = res.json()
            # Kiểm tra nếu kết quả trả về là dict mới lấy [cite: 7]
            return d if isinstance(d, dict) else None
    except:
        pass
    return None

def fetch_logic(endpoint, target_key, custom_params=None):
    results = []
    seen_slugs = set()
    print(f"\n[Săn tìm] {target_key}...")

    for year in YEARS:
        if len(results) >= TARGET_COUNT: break
        page = 1
        while len(results) < TARGET_COUNT:
            params = {"page": page, "year": year, "limit": 64}
            if custom_params:
                params.update(custom_params)
            
            url = f"{BASE_URL}/{endpoint}"
            data = get_data(url, params)
            
            # Fix lỗi AttributeError: Kiểm tra data phải là dict [cite: 25]
            if not isinstance(data, dict) or 'data' not in data or not isinstance(data['data'], dict):
                break 
            
            items = data['data'].get('items', [])
            if not items: break
            
            for item in items:
                if len(results) >= TARGET_COUNT: break
                if item['slug'] in seen_slugs: continue

                detail = get_data(f"https://phimapi.com/phim/{item['slug']}")
                if not isinstance(detail, dict) or 'movie' not in detail: continue
                
                m = detail['movie']
                
                # Khởi tạo biến an toàn để tránh lỗi logic
                lang_raw = str(m.get('lang', ''))
                sub_display = "Vietsub"
                if "Lồng Tiếng" in lang_raw: sub_display = "Lồng Tiếng"
                elif "Thuyết Minh" in lang_raw: sub_display = "Thuyết Minh"

                ep_total = str(m.get('episode_total', '')).lower()
                status = str(m.get('episode_current', '')).lower()
                country_list = m.get('country', [{}])
                country_name = country_list[0].get('name', '') if country_list else ''

                is_movie = (ep_total == "1" or "full" in status or "full" in ep_total)
                is_match = False

                if target_key == "anime_movie":
                    if is_movie: is_match = True
                elif target_key == "anime_nhat":
                    if country_name == "Nhật Bản" and not is_movie: is_match = True
                elif target_key == "hh_trung_quoc":
                    if country_name == "Trung Quốc" and not is_movie: is_match = True
                else:
                    is_match = True

                if is_match:
                    info = {
                        "name": m.get('name'), 
                        "year": year, 
                        "thumb": m.get('thumb_url'), 
                        "poster": m.get('poster_url'),
                        "slug": item['slug'],
                        "sub_type": sub_display,
                        "current_episode": m.get('episode_current', 'Full'),
                        "total_episodes": m.get('episode_total', '1'),
                        "country": country_name,
                        "type": m.get('type', 'series'),
                        "lang_raw": lang_raw 
                    }
                    results.append(info)
                    seen_slugs.add(item['slug'])
                    print(f"  + {len(results)}/{TARGET_COUNT}: {info['name']} ({year})")
                
                time.sleep(0.1) 
            page += 1
            if page > 10: break 
            
    return results

def main():
    final_data = {}
    
    # Theo chuẩn endpoint tài liệu [cite: 5, 24]
    final_data["phim_moi"] = fetch_logic("danh-sach/phim-moi-cap-nhat", "phim_moi")
    final_data["chieu_rap"] = fetch_logic("danh-sach/phim-chieu-rap", "chieu_rap")

    # Nhóm Hoạt hình
    final_data["anime_movie"] = fetch_logic("danh-sach/hoat-hinh", "anime_movie")
    final_data["anime_nhat"] = fetch_logic("quoc-gia/nhat-ban", "anime_nhat", {"category": "hoat-hinh"})
    final_data["hh_trung_quoc"] = fetch_logic("quoc-gia/trung-quoc", "hh_trung_quoc", {"category": "hoat-hinh"})

    # Nhóm Phim Lẻ & Bộ theo Quốc gia [cite: 86]
    countries = [
        ("viet-nam", "vn"), ("han-quoc", "han"), ("trung-quoc", "trung"), 
        ("thanh-lan", "thai"), ("au-my", "au_my")
    ]
    
    for c_slug, c_key in countries:
        final_data[f"le_{c_key}"] = fetch_logic(f"quoc-gia/{c_slug}", f"le_{c_key}", {"category": "phim-le"})
        final_data[f"bo_{c_key}"] = fetch_logic(f"quoc-gia/{c_slug}", f"bo_{c_key}", {"category": "phim-bo"})

    # Mix Top 10 phim bộ (4:3:2:1)
    final_data["top_10_bo"] = (final_data.get("bo_trung", [])[:4] + final_data.get("bo_han", [])[:3] + 
                               final_data.get("bo_au_my", [])[:2] + final_data.get("bo_thai", [])[:1])

    # Tổng hợp Thuyết minh & Lồng tiếng
    all_movies = []
    for k in final_data:
        if isinstance(final_data[k], list): all_movies.extend(final_data[k])
    
    unique_pool = {m['slug']: m for m in all_movies}.values()
    final_data["long_tieng"] = [m for m in unique_pool if "Lồng Tiếng" in m.get('lang_raw', '')][:15]
    final_data["thuyet_minh"] = [m for m in unique_pool if "Thuyết Minh" in m.get('lang_raw', '')][:15]

    with open("data_2026_perfect.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    print("\n[DONE] Đã lưu file thành công.")

if __name__ == "__main__":
    main()
