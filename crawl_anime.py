import requests
import json
import time
import random
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# --- CẤU HÌNH ---
BASE_URL = "https://phimapi.com/v1/api"
TARGET_COUNT = 15
MAX_WORKERS = 2
DATA_FILE = "data_2026_perfect.json"

def get_data(url, params=None):
    headers = {"User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/{random.randint(100, 115)}.0.0.0"}
    try:
        res = requests.get(url, params=params, timeout=15)
        if res.status_code == 200: return res.json()
    except: pass
    return None

def fetch_detail(slug):
    return get_data(f"https://phimapi.com/phim/{slug}")

def crawl_all_categories():
    """
    Quét tất cả phim mới để lấy dữ liệu cho các mục và thống kê ngôn ngữ
    """
    final_data = {
        "anime_movie": [], "anime_nhat": [], "hh_trung_quoc": [],
        "phim_chieu_rap": [], "long_tieng": [], "thuyet_minh": [],
        "le_vn": [], "bo_vn": [], "le_han": [], "bo_han": [],
        "le_trung": [], "bo_trung": [], "le_au_my": [], "bo_au_my": [],
        "le_thai": [], "bo_thai": []
    }
    
    seen_slugs = set()
    page = 1
    
    print("> Đang bắt đầu quét dữ liệu tổng hợp...")

    # Chạy cho đến khi hầu hết các mục quan trọng đều đủ 15 phim
    while page <= 25: # Quét sâu 25 trang để đảm bảo thống kê đủ Lồng tiếng/Thuyết minh
        url = f"{BASE_URL}/danh-sach/phim-moi"
        data = get_data(url, params={"page": page, "limit": 40})
        
        if not data or 'data' not in data or not data['data'].get('items'): break
            
        items = data['data']['items']
        slugs = [it['slug'] for it in items if it['slug'] not in seen_slugs]
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            details = list(executor.map(fetch_detail, slugs))
            
        for detail in details:
            if not detail or 'movie' not in detail: continue
            m = detail['movie']
            slug = m.get('slug')
            if slug in seen_slugs: continue
            
            # --- TRÍCH XUẤT THÔNG TIN ---
            countries = [c.get('name') for c in m.get('country', [])]
            primary_country = countries[0] if countries else ""
            m_type = m.get('type', '')
            ep_total = str(m.get('episode_total', '1'))
            is_movie = (m_type == 'single' or ep_total == "1")
            lang_raw = str(m.get('lang', '')).lower()
            categories = [c.get('name') for c in m.get('category', [])]
            
            # Tạo object phim chuẩn
            movie_obj = {
                "name": m.get('name'),
                "year": m.get('year'),
                "slug": slug,
                "thumb": m.get('thumb_url'),
                "poster": m.get('poster_url'),
                "sub_type": "Lồng Tiếng" if "lồng tiếng" in lang_raw else ("Thuyết Minh" if "thuyết minh" in lang_raw else "Vietsub"),
                "current_episode": m.get('episode_current', 'Full'),
                "total_episodes": ep_total,
                "country": primary_country,
                "description": m.get('content', '').replace('<p>', '').replace('</p>', '').strip()
            }

            # --- THỐNG KÊ VÀO DANH MỤC ---
            
            # 1. Thống kê theo Sub Type (Yêu cầu của ông)
            if "lồng tiếng" in lang_raw and len(final_data["long_tieng"]) < TARGET_COUNT:
                final_data["long_tieng"].append(movie_obj)
            if "thuyết minh" in lang_raw and len(final_data["thuyet_minh"]) < TARGET_COUNT:
                final_data["thuyet_minh"].append(movie_obj)

            # 2. Anime & Hoạt Hình
            if "Hoạt Hình" in categories:
                if is_movie and len(final_data["anime_movie"]) < TARGET_COUNT:
                    final_data["anime_movie"].append(movie_obj)
                elif primary_country == "Nhật Bản" and len(final_data["anime_nhat"]) < TARGET_COUNT:
                    final_data["anime_nhat"].append(movie_obj)
                elif primary_country == "Trung Quốc" and len(final_data["hh_trung_quoc"]) < TARGET_COUNT:
                    final_data["hh_trung_quoc"].append(movie_obj)

            # 3. Chiếu Rạp
            if m_type == 'hoathinh' or "Phim Chiếu Rạp" in categories:
                if len(final_data["phim_chieu_rap"]) < TARGET_COUNT:
                    final_data["phim_chieu_rap"].append(movie_obj)

            # 4. Phân loại Quốc Gia (Lẻ/Bộ)
            mapping = {
                "Việt Nam": "vn", "Hàn Quốc": "han", "Trung Quốc": "trung",
                "Âu Mỹ": "au_my", "Thái Lan": "thai"
            }
            if primary_country in mapping:
                suffix = mapping[primary_country]
                key = f"{'le' if is_movie else 'bo'}_{suffix}"
                if key in final_data and len(final_data[key]) < TARGET_COUNT:
                    final_data[key].append(movie_obj)

            seen_slugs.add(slug)

        print(f"  + Đã quét trang {page}. Lồng tiếng: {len(final_data['long_tieng'])}, Thuyết minh: {len(final_data['thuyet_minh'])}")
        
        # Điều kiện dừng: Nếu 2 mục quan trọng nhất đã đủ thì có thể nghỉ sớm
        if len(final_data["long_tieng"]) >= TARGET_COUNT and len(final_data["thuyet_minh"]) >= TARGET_COUNT:
            # Kiểm tra thêm các mục lẻ/bộ nếu muốn đủ 100% thì bỏ break này
            pass 
        
        page += 1
        time.sleep(0.1)

    return final_data

def main():
    start_time = time.time()
    
    # Chạy quét tổng hợp
    results = crawl_all_categories()

    # Thêm logic Trending (Trộn ngẫu nhiên)
    all_movies = []
    for k in results: all_movies.extend(results[k])
    random.shuffle(all_movies)
    results["trending_phim_bo"] = all_movies[:15]

    # Lưu file
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    print("\n" + "="*45)
    print(f"BÁO CÁO: Đã quét xong {DATA_FILE}")
    print(f"Tổng thời gian: {int(time.time() - start_time)}s")
    print("="*45)

if __name__ == "__main__":
    main()
