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
    # Dùng endpoint v1 cho đồng bộ với BASE_URL
    return get_data(f"{BASE_URL}/phim/{slug}")

def fetch_final(target_name, endpoint, country_target=None, is_movie_logic=None):
    results, local_seen = [], set()
    print(f"\n>>> Đang quét: {target_name}")
    
    for page in range(1, 31): # Quét sâu để lọc
        if len(results) >= TARGET_COUNT: break
        
        data = get_data(f"{BASE_URL}/danh-sach/{endpoint}", {"page": page, "limit": 40})
        if not data or 'data' not in data or not data['data'].get('items'): break
        
        items = data['data']['items']
        slugs_in_page = [it['slug'] for it in items]

        # Tải chi tiết song song để tiết kiệm thời gian
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            details_list = list(executor.map(fetch_detail, slugs_in_page))

        # Duyệt lại đúng thứ tự mảng trả về (Thứ tự của API)
        for d in details_list:
            if len(results) >= TARGET_COUNT: break
            if not d or 'data' not in d or 'item' not in d['data']: continue
            
            m = d['data']['item'] # Key chuẩn của endpoint v1/api/phim/
            slug = m.get('slug')
            if slug in local_seen: continue

            # LỌC NĂM: Chỉ lấy 2025, 2026
            m_year = int(m.get('year', 0))
            if m_year not in YEARS_FILTER: continue 
            
            # Kiểm tra Phim Lẻ/Bộ và Quốc gia
            countries = [c.get('name') for c in m.get('country', [])]
            m_type = m.get('type', '')
            ep_total = str(m.get('episode_total', '1'))
            is_movie = (m_type == 'single' or ep_total == "1")

            if (not country_target or country_target in countries) and \
               (is_movie_logic is None or is_movie == is_movie_logic):
                
                lang = str(m.get('lang', ''))
                results.append({
                    "name": m.get('name'),
                    "year": m_year,
                    "slug": slug,
                    "thumb": m.get('thumb_url'),
                    "poster": m.get('poster_url'),
                    "sub_type": "Lồng Tiếng" if "Lồng Tiếng" in lang else ("Thuyết Minh" if "Thuyết Minh" in lang else "Vietsub"),
                    "current_episode": m.get('episode_current', 'Full'),
                    "total_episodes": ep_total,
                    "country": countries[0] if countries else "",
                    "description": m.get('content', '').replace('<p>','').replace('</p>','').strip()
                })
                local_seen.add(slug)
                print(f"   [+] OK: {m.get('name')} ({m_year})")
                
    return results

def fetch_by_lang(lang_code, lang_name):
    """
    Riêng Lồng Tiếng / Thuyết Minh: Quét theo endpoint /nam/{year} để đảm bảo có hàng
    """
    results, local_seen = [], set()
    for year in YEARS_FILTER:
        if len(results) >= TARGET_COUNT: break
        data = get_data(f"{BASE_URL}/nam/{year}", {"page": 1, "sort_lang": lang_code, "limit": 40})
        if not data or 'data' not in data or not data['data'].get('items'): continue
        
        slugs = [it['slug'] for it in data['data']['items']]
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            details = list(executor.map(fetch_detail, slugs))

        for d in details:
            if len(results) >= TARGET_COUNT: break
            if not d or 'data' not in d or 'item' not in d['data']: continue
            m = d['data']['item']
            results.append({
                "name": m.get('name'), "year": year, "slug": m.get('slug'),
                "thumb": m.get('thumb_url'), "poster": m.get('poster_url'),
                "sub_type": lang_name, "current_episode": m.get('episode_current', 'Full'),
                "total_episodes": str(m.get('episode_total', '1')),
                "country": m.get('country', [{}])[0].get('name', ''),
                "description": m.get('content', '').replace('<p>','').replace('</p>','').strip()
            })
            local_seen.add(m.get('slug'))
    return results

# --- HÀM TRỘN TRENDING & MAIN GIỮ NGUYÊN NHƯ CŨ ---
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

    def run_and_report(key, name, endpoint, country=None, is_movie=None):
        res = fetch_final(name, endpoint, country, is_movie)
        final_data[key] = res
        report.append(f"| {name:22} | {'✅ ĐỦ' if len(res)>=TARGET_COUNT else f'⚠️ {len(res)}/15':16} |")

    # Quét các mục theo thứ tự API (Chỉ lấy 2025-2026)
    run_and_report("anime_movie", "Anime Movie", "hoat-hinh", is_movie=True)
    run_and_report("anime_nhat", "Anime Nhật", "hoat-hinh", country="Nhật Bản", is_movie=False)
    run_and_report("hh_trung_quoc", "HH Trung Quốc", "hoat-hinh", country="Trung Quốc", is_movie=False)
    run_and_report("phim_chieu_rap", "Phim Chiếu Rạp", "phim-chieu-rap")

    mapping = [("Việt Nam", "vn"), ("Hàn Quốc", "han"), ("Trung Quốc", "trung"), ("Âu Mỹ", "au_my"), ("Thái Lan", "thai")]
    for c_name, c_key in mapping:
        run_and_report(f"le_{c_key}", f"Lẻ {c_name}", "phim-le", country=c_name, is_movie=True)
        run_and_report(f"bo_{c_key}", f"Bộ {c_name}", "phim-bo", country=c_name, is_movie=False)

    # Trending & Lang
    final_data["trending_phim_bo"] = interleave_trending(final_data.get("bo_trung",[]), final_data.get("bo_han",[]), final_data.get("bo_au_my",[]), final_data.get("bo_thai",[]), final_data.get("phim_chieu_rap",[]))
    
    final_data["long_tieng"] = fetch_by_lang("long-tieng", "Lồng Tiếng")
    final_data["thuyet_minh"] = fetch_by_lang("thuyet-minh", "Thuyết Minh")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)

    print(f"\nHOÀN THÀNH TRONG {int(time.time()-start_time)}s")

if __name__ == "__main__":
    main()
