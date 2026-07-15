import requests, json, time, os, shutil
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "https://phimapi.com/v1/api"
LIMIT_COUNT = 1000
MAX_WORKERS = 2
OUTPUT_DIR = "data_categories"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'}

if not os.path.exists(OUTPUT_DIR): 
    os.makedirs(OUTPUT_DIR)

def get_data(url, params=None):
    for i in range(3):
        try:
            res = requests.get(url, params=params, headers=HEADERS, timeout=20)
            if res.status_code == 200:
                return res.json()
            else:
                print(f"DEBUG: API trả về mã lỗi {res.status_code} tại {url}")
            time.sleep(2)
        except Exception as e:
            print(f"DEBUG: Lỗi kết nối tại {url}: {e}")
            time.sleep(5)
    return None

def fetch_detail(slug):
    return get_data(f"{BASE_URL}/phim/{slug}")

def save_data(results, filename):
    file_path = os.path.join(OUTPUT_DIR, f"{filename}.json")
    
    # Kiểm tra ngưỡng 90%
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                old_data = json.load(f)
                if len(results) < len(old_data) * 0.9:
                    print(f"!!! Dữ liệu {filename} mới ({len(results)}) ít hơn 90% cũ ({len(old_data)}). Hủy cập nhật để bảo vệ file.")
                    return
            except: pass

    with open(file_path, "w", encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, separators=(',', ':'))
    print(f"-> Đã lưu thành công {len(results)} phim vào {filename}.json")

def process_and_add(items, results, seen):
    slugs = [it['slug'] for it in items if it['slug'] not in seen]
    if not slugs: return

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        details = list(executor.map(fetch_detail, slugs))
    
    for d in details:
        if len(results) >= LIMIT_COUNT: break
        if not d or 'data' not in d or 'item' not in d['data']: continue
        m = d['data']['item']
        
        # Lọc trailer/hoạt hình
        ep_current = str(m.get('episode_current', '')).lower()
        if any(x in ep_current for x in ["trailer", "sắp ra mắt", "coming soon"]): continue
        
        m_type = str(m.get('type', '')).lower().replace(" ", "")
        cat_slugs = [str(c.get('slug', '')).lower() for c in m.get('category', [])]
        if any(x in m_type for x in ['hoathinh', 'hoat-hinh']) or any(x in cat_slugs for x in ['hoat-hinh', 'anime']):
            continue 

        results.append({
            "name": m.get('name'), 
            "year": int(m.get('year', 0)), 
            "slug": m.get('slug'), 
            "thumb": m.get('thumb_url'), 
            "actor": m.get('actor', []), 
            "sub_type": m.get('lang', 'Vietsub'), 
            "current_episode": m.get('episode_current', 'Full'), 
            "total_episodes": str(m.get('episode_total', '1'))
        })
        seen.add(m.get('slug'))

def crawl_universal(display_name, filename, cat_slug=None, lang=None):
    results, seen = [], set()
    print(f"\n>>> Đang cào: {display_name}")
    
    # Quét từ 2026 về 1990
    for year in range(2026, 1989, -1):
        if len(results) >= LIMIT_COUNT: break
        print(f"  + Đang quét năm {year}...")
        
        page = 1
        while len(results) < LIMIT_COUNT:
            params = {"page": page, "limit": 40}
            if cat_slug is None:
                url = f"{BASE_URL}/nam/{year}"
                params.update({"sort_lang": lang})
            else:
                url = f"{BASE_URL}/the-loai/{cat_slug}"
                params.update({"year": year, "sort_field": "modified.time"})

            data = get_data(url, params)
            if not data or 'data' not in data or not data['data'].get('items'):
                break
            
            process_and_add(data['data']['items'], results, seen)
            page += 1
            time.sleep(0.8) 
            
    save_data(results, filename)

if __name__ == "__main__":
    targets = [
        ("Lồng Tiếng", "long_tieng", None, "long-tieng"), 
        ("Thuyết Minh", "thuyet_minh", None, "thuyet-minh"),
        ("Kinh Dị", "kinh_di", "kinh-di", None), 
        ("Hài Hước", "hai_huoc", "hai-huoc", None),
        ("Cổ Trang", "co_trang", "co-trang", None)
    ]
    for d_name, f_name, cat, lng in targets:
        crawl_universal(d_name, f_name, cat, lng)
