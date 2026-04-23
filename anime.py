import requests, json, time, os
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "https://phimapi.com/v1/api"
LIMIT_COUNT = 200
MAX_WORKERS = 2
OUTPUT_DIR = "data_categories"
if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

def get_data(url, params=None):
    try:
        res = requests.get(url, params=params, timeout=15)
        return res.json() if res.status_code == 200 else None
    except: return None

def fetch_detail(slug):
    return get_data(f"https://phimapi.com/phim/{slug}")

def crawl_hoat_hinh(name, filename, country=None, is_movie=None):
    results, seen = [], set()
    print(f">>> Đang hốt {name}...")
    for page in range(1, 40):
        if len(results) >= LIMIT_COUNT: break
        data = get_data(f"{BASE_URL}/danh-sach/hoat-hinh", {"page": page, "limit": 64})
        if not data: break
        items = data['data']['items']
        slugs = [it['slug'] for it in items if it['slug'] not in seen]
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            details = list(executor.map(fetch_detail, slugs))
        for d in details:
            if len(results) >= LIMIT_COUNT: break
            if not d or 'movie' not in d: continue
            m = d['movie']
            m_countries = [c.get('name') for c in m.get('country', [])]
            is_actually_movie = (m.get('type') == 'single' or str(m.get('episode_total')) == "1")
            if country and country not in m_countries: continue
            if is_movie is not None and is_actually_movie != is_movie: continue
            results.append({"name": m.get('name'), "year": int(m.get('year', 0)), "slug": m.get('slug'), "thumb": m.get('thumb_url'), "poster": m.get('poster_url'), "sub_type": "Lồng Tiếng" if "Lồng Tiếng" in str(m.get('lang','')) else "Thuyết Minh", "current_episode": m.get('episode_current', 'Full'), "total_episodes": str(m.get('episode_total', '1')), "country": m_countries[0] if m_countries else ""})
            seen.add(m['slug'])
    with open(os.path.join(OUTPUT_DIR, f"{filename}.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, separators=(',', ':'))

def crawl_rap():
    results, seen = [], set()
    print(">>> Đang hốt Phim Chiếu Rạp...")
    for year in [2026, 2025, 2024]:
        if len(results) >= LIMIT_COUNT: break
        data = get_data(f"{BASE_URL}/danh-sach/phim-chieu-rap", {"year": year, "page": 1, "limit": 64})
        if not data: continue
        for m in data['data']['items']:
            if len(results) >= LIMIT_COUNT: break
            results.append({"name": m.get('name'), "year": year, "slug": m.get('slug'), "thumb": m.get('thumb_url'), "poster": m.get('poster_url'), "sub_type": "Vietsub", "current_episode": "Full", "total_episodes": "1", "country": ""})
            seen.add(m['slug'])
    with open(os.path.join(OUTPUT_DIR, "phim_chieu_rap.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, separators=(',', ':'))

if __name__ == "__main__":
    crawl_hoat_hinh('Anime Movie', 'anime_movie', is_movie=True)
    crawl_hoat_hinh('Anime Nhật', 'anime_nhat', country='Nhật Bản', is_movie=False)
    crawl_hoat_hinh('HH Trung Quốc', 'hh_trung_quoc', country='Trung Quốc', is_movie=False)
    crawl_rap()
