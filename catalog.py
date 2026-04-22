import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "https://phimapi.com/v1/api/danh-sach/hoat-hinh"
DETAIL_URL = "https://phimapi.com/phim/"
LIMIT_COUNT = 20
MAX_WORKERS = 2 

def get_data(url, params=None):
    try:
        res = requests.get(url, params=params, timeout=10)
        return res.json() if res.status_code == 200 else None
    except: return None

def fetch_detail(slug):
    return get_data(f"{DETAIL_URL}{slug}")

def crawl_hoat_hinh_optimized(display_name, country_name=None, is_movie=None):
    results = []
    seen = set()
    print(f"\n>>> Đang hốt {display_name} (Chỉ quét trong mục Hoạt Hình)...")

    # Quét từ trang 1 đến 30 để vét đủ 200 phim mới nhất
    for page in range(1, 31):
        if len(results) >= LIMIT_COUNT: break
        
        data = get_data(BASE_URL, {"page": page, "limit": 64})
        if not data or 'data' not in data: break
        
        items = data['data']['items']
        slugs = [it['slug'] for it in items if it['slug'] not in seen]
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            details = list(executor.map(fetch_detail, slugs))

        for detail in details:
            if len(results) >= LIMIT_COUNT: break
            if not detail or 'movie' not in detail: continue
            m = detail['movie']
            
            # Lấy thông tin để lọc
            m_countries = [c.get('name') for c in m.get('country', [])]
            m_type = m.get('type', '')
            # Phim lẻ hoạt hình thường có type 'single' hoặc tổng số tập là 1
            is_actually_movie = (m_type == 'single' or str(m.get('episode_total', '1')) == "1")

            # --- BỘ LỌC THẲNG ---
            # 1. Nếu cần lọc Quốc gia (Nhật/Trung)
            if country_name and country_name not in m_countries: continue
            
            # 2. Nếu cần lọc Movie (Anime Movie) hoặc Bộ (Anime Nhật/HH Trung)
            if is_movie is True and not is_actually_movie: continue
            if is_movie is False and is_actually_movie: continue

            results.append({
                "name": m.get('name'),
                "year": m.get('year'),
                "slug": m.get('slug'),
                "thumb": m.get('thumb_url'),
                "sub_type": "Lồng Tiếng" if "Lồng Tiếng" in str(m.get('lang','')) else "Thuyết Minh",
                "current_episode": m.get('episode_current', 'Full'),
                "country": m_countries[0] if m_countries else ""
            })
            seen.add(m.get('slug'))
        
        print(f"  + {display_name}: Đã lấy {len(results)} phim (Trang {page})")
        time.sleep(0.1)

    return results

# Chạy thử 3 mục
anime_movie = crawl_hoat_hinh_optimized("Anime Movie", is_movie=True)
anime_nhat = crawl_hoat_hinh_optimized("Anime Nhật", country_name="Nhật Bản", is_movie=False)
hh_trung_quoc = crawl_hoat_hinh_optimized("HH Trung Quốc", country_name="Trung Quốc", is_movie=False)

# Lưu kết quả test
with open("test_hoat_hinh.json", "w", encoding="utf-8") as f:
    json.dump({
        "anime_movie": anime_movie,
        "anime_nhat": anime_nhat,
        "hh_trung_quoc": hh_trung_quoc
    }, f, ensure_ascii=False, separators=(',', ':'))

print("\n✅ Xong! Check file test_hoat_hinh.json là thấy đủ 3 mục cực chuẩn.")
