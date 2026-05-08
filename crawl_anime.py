import requests, json, time, os, random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# --- CẤU HÌNH ---
BASE_URL = "https://phimapi.com/v1/api"
YEARS_FILTER = [2026, 2025] 
TARGET_COUNT = 20
MAX_WORKERS = 2 
DATA_FILE = "data_2026_perfect.json"

def get_data(url, params=None):
    headers = {"User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(110, 125)}.0.0.0 Safari/537.36"}
    try:
        res = requests.get(url, params=params, timeout=15)
        if res.status_code == 200: return res.json()
    except: pass
    return None

def fetch_detail(slug):
    # Endpoint này trả về object có key là 'movie'
    return get_data(f"https://phimapi.com/phim/{slug}")

def fetch_final(target_name, endpoint, country_target=None, is_movie_logic=None):
    """
    Cào theo thứ tự API trả về, chỉ giữ lại phim 2025-2026
    """
    results, local_seen = [], set()
    print(f"> Đang quét: {target_name}...")
    
    for page in range(1, 25): # Quét rộng để lọc phim cũ
        if len(results) >= TARGET_COUNT: break
        
        url = f"{BASE_URL}/danh-sach/{endpoint}"
        params = {"page": page, "limit": 40}
        data = get_data(url, params)
        
        if not data or 'data' not in data or not data['data'].get('items'): break
        items = data['data']['items']
        
        # Duyệt từng item theo đúng thứ tự API trả về (Cực kỳ quan trọng)
        for item in items:
            if len(results) >= TARGET_COUNT: break
            slug = item['slug']
            if slug in local_seen: continue
            
            # Lấy chi tiết để kiểm tra năm và quốc gia
            detail = fetch_detail(slug)
            if not detail or 'movie' not in detail: continue
            m = detail['movie']
            
            # 1. Kiểm tra năm trước (Ưu tiên thứ tự xuất hiện)
            m_year = int(m.get('year', 0))
            if m_year not in YEARS_FILTER:
                continue 
            
            # 2. Kiểm tra các điều kiện lọc khác
            countries = [c.get('name') for c in m.get('country', [])]
            m_type = m.get('type', '')
            ep_total_val = str(m.get('episode_total', '1'))
            is_movie = (m_type == 'single' or ep_total_val == "1")

            if (not country_target or country_target in countries) and \
               (is_movie_logic is None or is_movie == is_movie_logic):
                
                lang = str(m.get('lang', ''))
                desc = m.get('content', '').replace('<p>', '').replace('</p>', '').replace('\n', ' ').strip()

                # Thêm vào theo đúng thứ tự quét được
                results.append({
                    "name": m.get('name'),
                    "year": m_year,
                    "slug": m.get('slug'),
                    "thumb": m.get('thumb_url'),
                    "poster": m.get('poster_url'),
                    "sub_type": "Lồng Tiếng" if "Lồng Tiếng" in lang else ("Thuyết Minh" if "Thuyết Minh" in lang else "Vietsub"),
                    "current_episode": m.get('episode_current', 'Full'),
                    "total_episodes": ep_total_val,
                    "country": countries[0] if countries else "",
                    "description": desc
                })
                local_seen.add(slug)
                print(f"   [+] Đã lấy: {m.get('name')} ({m_year})")
                
    return results

# Các hàm fetch_by_lang và main giữ nguyên như bản trước 
# (Nhớ copy lại hàm fetch_by_lang và phần xử lý main từ bản code cũ của tui)
