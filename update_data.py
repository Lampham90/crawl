import requests
import json
import os
import time
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# --- CẤU HÌNH ---
BASE_URL = "https://phimapi.com/v1/api"
YEARS_FILTER = [2026, 2025]
OUTPUT_DIR = "data_categories"  # Thư mục chứa các file JSON con
MAX_WORKERS = 2  
MAX_ITEMS_PER_CAT = 30  

def get_data(url, params=None):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        res = requests.get(url, params=params, headers=headers, timeout=10)
        if res.status_code == 200: 
            return res.json()
    except Exception as e:
        pass
    return None

def fetch_detail(slug):
    time.sleep(random.uniform(0.1, 0.3)) 
    return get_data(f"{BASE_URL}/phim/{slug}")

def parse_movie(m):
    lang = str(m.get('lang', ''))
    return {
        "name": m.get('name'),
        "year": int(m.get('year', 0)),
        "slug": m.get('slug'),
        "thumb": m.get('thumb_url'),
        "poster": m.get('poster_url'),
        "sub_type": "Lồng Tiếng" if "Lồng Tiếng" in lang else ("Thuyết Minh" if "Thuyết Minh" in lang else "Vietsub"),
        "current_episode": m.get('episode_current', 'Full'),
        "total_episodes": str(m.get('episode_total', '1')),
        "country": m.get('country', [{}])[0].get('name', ''),
        "description": m.get('content', '').replace('<p>','').replace('</p>','').replace('<br>', '').strip()
    }

def update_category_list(current_list, new_movies, max_count=MAX_ITEMS_PER_CAT):
    # Tránh lỗi nếu current_list bị None hoặc lỗi cấu trúc
    if not isinstance(current_list, list):
        current_list = []
    movie_dict = {m['slug']: m for m in current_list if isinstance(m, dict) and 'slug' in m}
    
    for m in reversed(new_movies):
        if isinstance(m, dict) and 'slug' in m:
            movie_dict[m['slug']] = m
        
    new_slugs = {nm['slug'] for nm in new_movies if isinstance(nm, dict) and 'slug' in nm}
    newly_added = [movie_dict[s] for s in new_slugs if s in movie_dict]
    old_maintained = [m for s, m in movie_dict.items() if s not in new_slugs]
    
    final_ordered = newly_added + old_maintained
    return final_ordered[:max_count]

def interleave_trending(rap, tr, han, viet, au):
    trending = []
    l_rap, l_tr, l_han, l_viet, l_au = list(rap), list(tr), list(han), list(viet), list(au)
    
    while (l_rap or l_tr or l_han or l_viet or l_au) and len(trending) < 15:
        if l_rap: trending.append(l_rap.pop(0))
        if l_tr: trending.append(l_tr.pop(0))
        if l_han: trending.append(l_han.pop(0))
        if l_viet: trending.append(l_viet.pop(0))
        if l_au: trending.append(l_au.pop(0))
            
    return trending[:15]

def main():
    start_time = time.time()
    
    # 1. Chắc chắn thư mục được tạo ra bất kể môi trường nào
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    category_keys = [
        "anime_movie", "anime_nhat", "hh_trung_quoc", "phim_chieu_rap",
        "le_vn", "bo_vn", "le_han", "bo_han", "le_trung", "bo_trung",
        "le_au_my", "bo_au_my", "le_thai", "bo_thai", 
        "long_tieng", "thuyet_minh", "trending_phim_bo"
    ]
    
    final_data = {}
    
    # 2. Đọc dữ liệu cũ (Nếu chưa có file thì tự khởi tạo list rỗng, không báo lỗi đứt gánh)
    print(f"📖 Đang nạp dữ liệu từ thư mục /{OUTPUT_DIR}...")
    for key in category_keys:
        file_path = os.path.join(OUTPUT_DIR, f"{key}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    final_data[key] = json.load(f)
            except:
                final_data[key] = []
        else:
            final_data[key] = []
            
    # Tách từ file tổng cũ nếu có nằm ở thư mục gốc
    if all(len(v) == 0 for v in final_data.values()) and os.path.exists("data_2026_perfect.json"):
        print("💡 Phát hiện file tổng cũ ở ngoài, đang tách dữ liệu...")
        try:
            with open("data_2026_perfect.json", "r", encoding="utf-8") as f:
                old_data = json.load(f)
                for k, v in old_data.items():
                    if k in final_data:
                        final_data[k] = v
        except:
            pass

    # 3. Bào 10 trang đầu của Phim Mới Cập Nhật
    print(">>> Đang quét 10 trang đầu từ API Phim Mới Cập Nhật...")
    raw_items = []
    for page in range(1, 11):
        data = get_data(f"{BASE_URL}/danh-sach/phim-moi-cap-nhat", {"page": page, "limit": 40})
        if data and 'data' in data and data['data'].get('items'):
            items = data['data']['items']
            raw_items.extend(items)
            print(f"   -> Đã lấy trang {page} ({len(items)} phim)")
        else:
            print(f"   -> Trang {page} trống hoặc lỗi.")
        time.sleep(0.3)

    if not raw_items:
        print("❌ Không thu thập được phim mới nào từ API. Dừng lại để giữ an toàn.")
        return

    # 4. Phân loại phim mới
    categorized = {k: [] for k in category_keys}
    seen_slugs_this_run = set()
    unique_items = [item for item in raw_items if item['slug'] not in seen_slugs_this_run and not seen_slugs_this_run.add(item['slug'])]

    print(f" Tổng số phim độc nhất cần check chi tiết: {len(unique_items)}")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        details = list(executor.map(fetch_detail, [it['slug'] for it in unique_items]))

    for d in details:
        if not d or 'data' not in d or 'item' not in d['data']: continue
            
        m = d['data']['item']
        if int(m.get('year', 0)) not in YEARS_FILTER: continue
            
        ep_current = str(m.get('episode_current', '')).lower()
        if any(x in ep_current for x in ["trailer", "sắp ra mắt", "coming soon", "tập 0"]): continue

        movie_data = parse_movie(m)
        m_type = m.get('type', '')
        is_movie = (m_type == 'single' or str(m.get('episode_total')) == "1")
        countries = [c.get('name') for c in m.get('country', [])]
        categories = [g.get('name') for g in m.get('category', [])]
        chude = m.get('chude', '')
        lang = str(m.get('lang', ''))

        if "Hoạt Hình" in categories:
            if is_movie: categorized["anime_movie"].append(movie_data)
            elif "Nhật Bản" in countries: categorized["anime_nhat"].append(movie_data)
            elif "Trung Quốc" in countries: categorized["hh_trung_quoc"].append(movie_data)

        if "chieu-rap" in chude or m.get('phim_chieu_rap') is True: 
            categorized["phim_chieu_rap"].append(movie_data)

        if "Việt Nam" in countries:
            categorized["le_vn" if is_movie else "bo_vn"].append(movie_data)
        elif "Hàn Quốc" in countries:
            categorized["le_han" if is_movie else "bo_han"].append(movie_data)
        elif "Trung Quốc" in countries:
            categorized["le_trung" if is_movie else "bo_trung"].append(movie_data)
        elif any(c in countries for c in ["Âu Mỹ", "Mỹ", "Anh"]):
            categorized["le_au_my" if is_movie else "bo_au_my"].append(movie_data)
        elif "Thái Lan" in countries:
            categorized["le_thai" if is_movie else "bo_thai"].append(movie_data)

        if "Lồng Tiếng" in lang: categorized["long_tieng"].append(movie_data)
        if "Thuyết Minh" in lang: categorized["thuyet_minh"].append(movie_data)

    # 5. Gộp dữ liệu mới vào dữ liệu cũ
    for key in category_keys:
        if key in categorized and categorized[key]:
            final_data[key] = update_category_list(final_data[key], categorized[key])

    # 6. Xử lý lại danh mục trộn Mix Trending
    final_data["trending_phim_bo"] = interleave_trending(
        final_data.get("phim_chieu_rap", []),
        final_data.get("bo_trung", []), 
        final_data.get("bo_han", []),
        final_data.get("le_vn", []), 
        final_data.get("bo_au_my", [])
    )

    # 7. Lưu đè ra từng file JSON con
    for key, value in final_data.items():
        file_path = os.path.join(OUTPUT_DIR, f"{key}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=4)
            
    print(f"\n🚀 HOÀN THÀNH: Cập nhật thư mục '{OUTPUT_DIR}' sau {int(time.time()-start_time)} giây!")

if __name__ == "__main__":
    main()
