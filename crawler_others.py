import requests, json, time, os
from datetime import datetime

BASE_URL = "https://phimapi.com/v1/api"
LIMIT_COUNT = 1000
OUTPUT_DIR = "data_categories"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'}

if not os.path.exists(OUTPUT_DIR): 
    os.makedirs(OUTPUT_DIR)

def get_data(url, params=None):
    for i in range(3): # Thử lại 3 lần
        try:
            res = requests.get(url, params=params, headers=HEADERS, timeout=20)
            if res.status_code == 200:
                return res.json()
            elif res.status_code == 429:
                print(f"!!! Bị chặn (429) tại {url}. Nghỉ 60 giây...")
                time.sleep(60) 
            else:
                print(f"DEBUG: Mã lỗi {res.status_code} tại {url}")
            time.sleep(5)
        except Exception as e:
            print(f"DEBUG: Lỗi kết nối: {e}")
            time.sleep(10)
    return None

def save_data(results, filename):
    file_path = os.path.join(OUTPUT_DIR, f"{filename}.json")
    
    # Đã bỏ phần kiểm tra dữ liệu cũ để luôn ghi đè file mới
    with open(file_path, "w", encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, separators=(',', ':'))
    print(f"-> Đã lưu {len(results)} phim vào {filename}.json")

def process_and_add(items, results, seen):
    for it in items:
        if len(results) >= LIMIT_COUNT: break
        if it['slug'] in seen: continue
        
        # Gọi chi tiết từng phim một cách tuần tự
        d = get_data(f"{BASE_URL}/phim/{it['slug']}")
        if not d or 'data' not in d or 'item' not in d['data']: continue
        
        m = d['data']['item']
        
        # Lọc Trailer & Hoạt hình
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
        time.sleep(1.2) # Nghỉ giữa mỗi phim để tránh bị 429

def crawl_universal(display_name, filename, cat_slug=None, lang=None):
    results, seen = [], set()
    print(f"\n>>> Bắt đầu cào: {display_name}")
    
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
