import requests
import json
import time
import os
from concurrent.futures import ThreadPoolExecutor

# --- CẤU HÌNH TEST ---
BASE_URL = "https://phimapi.com/v1/api"
# Quét từ 2026 ngược về 2020 để đảm bảo ĐỦ 200 phim cho mỗi mục
YEARS = [2026, 2025, 2024, 2023, 2022, 2021, 2020]
LIMIT_COUNT = 50
MAX_WORKERS = 2 # Tăng worker để test cho lẹ

def get_data(url, params=None):
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200: return res.json()
    except: pass
    return None

def fetch_detail(slug):
    return get_data(f"https://phimapi.com/phim/{slug}")

def crawl_anime_only(display_name, filename, country=None, is_movie=None):
    results = []
    seen = set()
    print(f"\n>>> ĐANG LỌC RIÊNG: {display_name}...")

    for year in YEARS:
        if len(results) >= LIMIT_COUNT: break
        
        # Endpoint chuyên biệt cho hoạt hình
        url = f"{BASE_URL}/danh-sach/hoat-hinh"
        
        for page in range(1, 25): # Quét cực sâu 25 trang mỗi năm
            if len(results) >= LIMIT_COUNT: break
            
            data = get_data(url, {"year": year, "page": page, "limit": 64})
            if not data or 'data' not in data or not data['data'].get('items'): break
            
            items = data['data']['items']
            slugs_to_fetch = [it['slug'] for it in items if it['slug'] not in seen]
            
            if not slugs_to_fetch: continue

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                details = list(executor.map(fetch_detail, slugs_to_fetch))

            for detail in details:
                if len(results) >= LIMIT_COUNT: break
                if not detail or 'movie' not in detail: continue
                m = detail['movie']
                
                # --- LOGIC LỌC KHẮT KHE ---
                m_countries = [c.get('name') for c in m.get('country', [])]
                m_type = m.get('type', '')
                is_actually_movie = (m_type == 'single' or str(m.get('episode_total')) == "1")

                # 1. Lọc theo Quốc gia (Nếu có yêu cầu)
                if country and country not in m_countries: continue
                
                # 2. Lọc theo định dạng Lẻ (Movie) hoặc Bộ (Series)
                if is_movie is True and not is_actually_movie: continue
                if is_movie is False and is_actually_movie: continue

                results.append({
                    "name": m.get('name'),
                    "year": int(m.get('year', 0)),
                    "slug": m.get('slug'),
                    "thumb": m.get('thumb_url'),
                    "sub_type": "Lồng Tiếng" if "Lồng Tiếng" in str(m.get('lang','')) else "Thuyết Minh",
                    "current_episode": m.get('episode_current', 'Full'),
                    "country": m_countries[0] if m_countries else ""
                })
                seen.add(m.get('slug'))
            
            print(f"  + {display_name} ({year}): Đã hốt {len(results)}/{LIMIT_COUNT}")
            time.sleep(0.1)

    # Xuất file test
    with open(f"{filename}.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, separators=(',', ':'))
    print(f"✅ Xong mục {display_name}! Xuất file: {filename}.json")

def main():
    # TEST RIÊNG 3 MỤC NÀY
    # 1. Anime Movie: Hoạt hình + Movie (Không phân biệt quốc gia)
    crawl_anime_only("Anime Movie", "test_anime_movie", is_movie=True)
    
    # 2. Anime Nhật: Hoạt hình + Nhật Bản + Phim bộ
    crawl_anime_only("Anime Nhật", "test_anime_nhat", country="Nhật Bản", is_movie=False)
    
    # 3. HH Trung Quốc: Hoạt hình + Trung Quốc + Phim bộ
    crawl_anime_only("HH Trung Quốc", "test_hh_trung_quoc", country="Trung Quốc", is_movie=False)

if __name__ == "__main__":
    main()
