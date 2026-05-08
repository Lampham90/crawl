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
        "description": m.get('content', '').replace('<p>','').replace('</p>','').strip()
    }

def fetch_universal(target_name, endpoint, country_target=None, is_movie_logic=None):
    results, local_seen = [], set()
    print(f">>> Đang bào: {target_name}...")
    for page in range(1, 31):
        if len(results) >= TARGET_COUNT: break
        data = get_data(f"{BASE_URL}/danh-sach/{endpoint}", {"page": page, "limit": 40})
        if not data or 'data' not in data or not data['data'].get('items'): break
        items = data['data']['items']
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            details = list(executor.map(fetch_detail, [it['slug'] for it in items]))
        for d in details:
            if len(results) >= TARGET_COUNT: break
            if not d or 'data' not in d or 'item' not in d['data']: continue
            m = d['data']['item']
            if int(m.get('year', 0)) not in YEARS_FILTER: continue
            countries = [c.get('name') for c in m.get('country', [])]
            m_type = m.get('type', '')
            is_movie = (m_type == 'single' or str(m.get('episode_total')) == "1")
            if (not country_target or country_target in countries) and (is_movie_logic is None or is_movie == is_movie_logic):
                results.append(parse_movie(m))
                local_seen.add(m['slug'])
    return results

def fetch_special_lang(target_name, lang_code):
    results = []
    print(f">>> Đang bào: {target_name}...")
    for year in YEARS_FILTER:
        if len(results) >= TARGET_COUNT: break
        data = get_data(f"{BASE_URL}/nam/{year}", {"page": 1, "limit": 40, "sort_lang": lang_code})
        if not data or 'data' not in data or not data['data'].get('items'): continue
        items = data['data']['items']
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            details = list(executor.map(fetch_detail, [it['slug'] for it in items]))
        for d in details:
            if len(results) >= TARGET_COUNT: break
            if not d or 'data' not in d or 'item' not in d['data']: continue
            m = d['data']['item']
            results.append(parse_movie(m))
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

    # 1. Các mục thông thường
    targets = [
        ("anime_movie", "Anime Movie", "hoat-hinh", None, True),
        ("anime_nhat", "Anime Nhật", "hoat-hinh", "Nhật Bản", False),
        ("hh_trung_quoc", "HH Trung Quốc", "hoat-hinh", "Trung Quốc", False),
        ("phim_chieu_rap", "Phim Chiếu Rạp", "phim-chieu-rap", None, None)
    ]
    for key, name, endp, countr, is_m in targets:
        res = fetch_universal(name, endp, countr, is_m)
        final_data[key] = res
        report.append(f"| {name:22} | {'✅ ĐỦ' if len(res)>=TARGET_COUNT else f'⚠️ {len(res)}/15':16} |")

    # 2. Quốc gia
    mapping = [("Việt Nam", "vn"), ("Hàn Quốc", "han"), ("Trung Quốc", "trung"), ("Âu Mỹ", "au_my"), ("Thái Lan", "thai")]
    for c_name, c_key in mapping:
        res_le = fetch_universal(f"Lẻ {c_name}", "phim-le", c_name, True)
        res_bo = fetch_universal(f"Bộ {c_name}", "phim-bo", c_name, False)
        final_data[f"le_{c_key}"], final_data[f"bo_{c_key}"] = res_le, res_bo
        report.append(f"| Lẻ {c_name:19} | {'✅' if len(res_le)>=TARGET_COUNT else len(res_le)} |")
        report.append(f"| Bộ {c_name:19} | {'✅' if len(res_bo)>=TARGET_COUNT else len(res_bo)} |")

    # 3. Lồng Tiếng & Thuyết Minh
    lt = fetch_special_lang("Lồng Tiếng", "long-tieng")
    tm = fetch_special_lang("Thuyết Minh", "thuyet-minh")
    final_data["long_tieng"], final_data["thuyet_minh"] = lt, tm
    report.append(f"| {'Lồng Tiếng':22} | {'✅' if len(lt)>=TARGET_COUNT else len(lt)} |")
    report.append(f"| {'Thuyết Minh':22} | {'✅' if len(tm)>=TARGET_COUNT else len(tm)} |")

    # 4. HÀNG MIX (TRENDING) - ĐÃ QUAY TRỞ LẠI
    final_data["trending_phim_bo"] = interleave_trending(
        final_data.get("bo_trung", []), final_data.get("bo_han", []),
        final_data.get("bo_au_my", []), final_data.get("bo_thai", []),
        final_data.get("phim_chieu_rap", [])
    )
    report.append(f"| {'Top Trending (Mix)':22} | {'🔥 MIXED':16} |")

    # Lưu và Báo cáo
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)

    print("\n" + "="*45 + f"\n| BÁO CÁO CRAWL - {datetime.now().strftime('%d/%m %H:%M')} |\n" + "-"*45)
    for line in report: print(line)
    print("="*45 + f"\nTime: {int(time.time()-start_time)}s\n")

if __name__ == "__main__":
    main()
