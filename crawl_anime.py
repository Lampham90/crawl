import requests, json, time, os, random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# --- CẤU HÌNH ---
BASE_URL = "https://phimapi.com/v1/api"
YEARS_FILTER = [2026, 2025] 
TARGET_COUNT = 15
MAX_WORKERS = 2
DATA_FILE = "data_2026_perfect.json"

def get_data(url, params=None):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200: return res.json()
    except: pass
    return None

def fetch_detail(slug):
    return get_data(f"{BASE_URL}/phim/{slug}")

def fetch_universal(target_name, endpoint="phim-moi-cap-nhat", country_target=None, is_movie_logic=None, lang_filter=None):
    """
    Hàm quét tổng lực: Áp dụng cho cả Thể loại, Quốc gia và Lồng tiếng/Thuyết minh
    Luôn ưu tiên thứ tự API trả về và lọc năm 2025-2026.
    """
    results, local_seen = [], set()
    print(f">>> Đang bào: {target_name}...")
    
    # Quét sâu 40 trang để đảm bảo tìm đủ phim hiếm (như Lồng tiếng)
    for page in range(1, 41): 
        if len(results) >= TARGET_COUNT: break
        
        # Nếu là Lồng tiếng/Thuyết minh thì dùng endpoint 'phim-moi-cap-nhat' để lấy hàng mới nhất
        url = f"{BASE_URL}/danh-sach/{endpoint}"
        data = get_data(url, {"page": page, "limit": 40})
        
        if not data or 'data' not in data or not data['data'].get('items'): break
        items = data['data']['items']
        slugs_in_page = [it['slug'] for it in items]

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            details_list = list(executor.map(fetch_detail, slugs_in_page))

        for d in details_list:
            if len(results) >= TARGET_COUNT: break
            if not d or 'data' not in d or 'item' not in d['data']: continue
            
            m = d['data']['item']
            slug = m.get('slug')
            if slug in local_seen: continue

            # 1. Lọc năm 2025-2026
            m_year = int(m.get('year', 0))
            if m_year not in YEARS_FILTER: continue 
            
            # 2. Lọc ngôn ngữ (Nếu có yêu cầu Lồng tiếng/Thuyết minh)
            m_lang = str(m.get('lang', ''))
            if lang_filter and lang_filter not in m_lang: continue

            # 3. Lọc Phim Lẻ/Bộ và Quốc gia
            countries = [c.get('name') for c in m.get('country', [])]
            m_type = m.get('type', '')
            ep_total = str(m.get('episode_total', '1'))
            is_movie = (m_type == 'single' or ep_total == "1")

            if (not country_target or country_target in countries) and \
               (is_movie_logic is None or is_movie == is_movie_logic):
                
                results.append({
                    "name": m.get('name'),
                    "year": m_year,
                    "slug": slug,
                    "thumb": m.get('thumb_url'),
                    "poster": m.get('poster_url'),
                    "sub_type": "Lồng Tiếng" if "Lồng Tiếng" in m_lang else ("Thuyết Minh" if "Thuyết Minh" in m_lang else "Vietsub"),
                    "current_episode": m.get('episode_current', 'Full'),
                    "total_episodes": ep_total,
                    "country": countries[0] if countries else "",
                    "description": m.get('content', '').replace('<p>','').replace('</p>','').strip()
                })
                local_seen.add(slug)
                
    return results

def interleave_trending(tr, han, au, thai, rap):
    trending = []
    l_tr, l_han, l_au, l_thai, l_rap = list(tr[:4]), list(han[:3]), list(au[:3]), list(thai[:2]), list(rap[:3])
    while l_tr or l_han or l_au or l_thai or l_rap:
        if l_tr: trending.append(l_tr.pop(0))
        if l_rap: trending.append(l_rap.pop(0))
        if l_han: trending.append(l_han.pop(0))
        if l_au: trending.append(l_au.pop(0))
        if l_thai: trending.append(l_thai.pop(0))
    random.shuffle(trending)
    return trending[:15]

def main():
    start_time = time.time()
    final_data, report = {}, []

    def run_task(key, name, endpoint="phim-moi-cap-nhat", country=None, is_movie=None, lang=None):
        res = fetch_universal(name, endpoint, country, is_movie, lang)
        final_data[key] = res
        status = "✅ ĐỦ" if len(res) >= TARGET_COUNT else f"⚠️ {len(res)}/15"
        report.append(f"| {name:22} | {status:16} |")

    # --- TIẾN HÀNH CÀO ---
    run_task("anime_movie", "Anime Movie", "hoat-hinh", is_movie=True)
    run_task("anime_nhat", "Anime Nhật", "hoat-hinh", country="Nhật Bản", is_movie=False)
    run_task("hh_trung_quoc", "HH Trung Quốc", "hoat-hinh", country="Trung Quốc", is_movie=False)
    run_task("phim_chieu_rap", "Phim Chiếu Rạp", "phim-chieu-rap")

    # Phim theo quốc gia
    mapping = [("Việt Nam", "vn"), ("Hàn Quốc", "han"), ("Trung Quốc", "trung"), ("Âu Mỹ", "au_my"), ("Thái Lan", "thai")]
    for c_name, c_key in mapping:
        run_task(f"le_{c_key}", f"Lẻ {c_name}", "phim-le", country=c_name, is_movie=True)
        run_task(f"bo_{c_key}", f"Bộ {c_name}", "phim-bo", country=c_name, is_movie=False)

    # Lồng Tiếng & Thuyết Minh (Áp dụng chung logic quét mới nhất)
    run_task("long_tieng", "Lồng Tiếng", lang="Lồng Tiếng")
    run_task("thuyet_minh", "Thuyết Minh", lang="Thuyết Minh")

    # Mix Trending
    final_data["trending_phim_bo"] = interleave_trending(final_data.get("bo_trung",[]), final_data.get("bo_han",[]), final_data.get("bo_au_my",[]), final_data.get("bo_thai",[]), final_data.get("phim_chieu_rap",[]))
    report.append(f"| {'Top Trending':22} | {'🔥 MIXED':16} |")

    # Lưu dữ liệu
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)

    # --- BẢN BÁO CÁO CỦA NÍ ĐÂY ---
    print("\n" + "="*45)
    print(f"    BÁO CÁO CRAWL - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("="*45)
    print(f"| {'Hạng mục':22} | {'Trạng thái':16} |")
    print("-" * 45)
    for line in report: print(line)
    print("="*45)
    print(f"Tổng thời gian: {int(time.time() - start_time)}s\n")

if __name__ == "__main__":
    main()
