import requests
import json
import os
import time
import random
from concurrent.futures import ThreadPoolExecutor

# --- CẤU HÌNH ---
# Sử dụng chính xác endpoint gốc không qua v1/api nữa
BASE_URL = "https://phimapi.com"
YEARS_FILTER = [2026, 2025]
OUTPUT_DIR = "data_categories"
MAX_WORKERS = 2  
MAX_ITEMS_PER_CAT = 30  
REPORT_FILE = "update_report.json"

def get_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    for attempt in range(3):
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200: 
                return res.json()
            elif res.status_code in [429, 502, 503]:
                time.sleep(random.uniform(1.5, 3.0))
        except:
            time.sleep(1.5)
    return None

def fetch_detail(slug):
    time.sleep(random.uniform(0.2, 0.4)) 
    # API chi tiết phim thì vẫn nằm ở v1/api/phim/{slug} chuẩn của hệ thống
    return get_data(f"{BASE_URL}/v1/api/phim/{slug}")

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
        "description": m.get('content', '').replace('<p>','').replace('</p>','').replace('<br>', '').strip()
    }

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    category_keys = [
        "anime_movie", "anime_nhat", "hh_trung_quoc", "phim_chieu_rap",
        "le_vn", "bo_vn", "le_han", "bo_han", "le_trung", "bo_trung",
        "le_au_my", "bo_au_my", "le_thai", "bo_thai", 
        "long_tieng", "thuyet_minh"
    ]
    
    final_data = {}
    for key in category_keys:
        file_path = os.path.join(OUTPUT_DIR, f"{key}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f: final_data[key] = json.load(f)
            except: final_data[key] = []
        else: final_data[key] = []

    print(">>> Đang quét 10 trang đầu từ API Phim Mới Cập Nhật...")
    raw_items = []
    for page in range(1, 11):
        # 🌟 Gọi chuẩn URL ní đưa kèm tham số page
        url = f"{BASE_URL}/danh-sach/phim-moi-cap-nhat?page={page}"
        data = get_data(url)
        
        # Cấu trúc trả về của endpoint này là mảng items nằm ở gốc hoặc trong data tùy bản update
        items = []
        if data:
            if isinstance(data, dict):
                if 'items' in data: items = data['items']
                elif 'data' in data and 'items' in data['data']: items = data['data']['items']
        
        if items:
            raw_items.extend(items)
            print(f"-> Đã lấy thành công trang {page}/10 ({len(items)} phim)")
        else:
            print(f"-> Trang {page}/10 lỗi hoặc không có dữ liệu.")
        time.sleep(0.3)

    if not raw_items:
        print("❌ Không lấy được dữ liệu mới từ API. Vui lòng kiểm tra lại kết nối.")
        return

    print(f"✅ Thu thập được {len(raw_items)} phim thô. Đang lọc trùng lặp...")
    seen_slugs = set()
    unique_items = [it for it in raw_items if it.get('slug') and it['slug'] not in seen_slugs and not seen_slugs.add(it['slug'])]
    print(f"🎯 Còn lại {len(unique_items)} phim duy nhất. Tiến hành lấy chi tiết phân loại...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        details = list(executor.map(fetch_detail, [it['slug'] for it in unique_items]))

    report_details = []
    categorized = {k: [] for k in category_keys}

    for d in details:
        if not d or 'data' not in d or 'item' not in d['data']: continue
        m = d['data']['item']
        if int(m.get('year', 0)) not in YEARS_FILTER: continue
        
        ep_current = str(m.get('episode_current', '')).lower()
        if any(x in ep_current for x in ["trailer", "sắp ra mắt", "coming soon", "tập 0"]): continue

        movie_data = parse_movie(m)
        m_type = m.get('type', '')
        is_movie = (m_type == 'single' or str(m.get('episode_total')) == "1")
        countries = [c.get('name') for c in m.get('country', [])]
        categories = [g.get('name') for g in m.get('category', [])]
        chude = m.get('chude', '')
        lang = str(m.get('lang', ''))

        if "Hoạt Hình" in categories:
            if is_movie: categorized["anime_movie"].append(movie_data)
            elif "Nhật Bản" in countries: categorized["anime_nhat"].append(movie_data)
            elif "Trung Quốc" in countries: categorized["hh_trung_quoc"].append(movie_data)
        if "chieu-rap" in chude or m.get('phim_chieu_rap') is True: 
            categorized["phim_chieu_rap"].append(movie_data)
        if "Việt Nam" in countries: categorized["le_vn" if is_movie else "bo_vn"].append(movie_data)
        elif "Hàn Quốc" in countries: categorized["le_han" if is_movie else "bo_han"].append(movie_data)
        elif "Trung Quốc" in countries: categorized["le_trung" if is_movie else "bo_trung"].append(movie_data)
        elif any(c in countries for c in ["Âu Mỹ", "Mỹ", "Anh"]): categorized["le_au_my" if is_movie else "bo_au_my"].append(movie_data)
        elif "Thái Lan" in countries: categorized["le_thai" if is_movie else "bo_thai"].append(movie_data)
        if "Lồng Tiếng" in lang: categorized["long_tieng"].append(movie_data)
        if "Thuyết Minh" in lang: categorized["thuyet_minh"].append(movie_data)

    for key in category_keys:
        if not categorized[key]: continue
        
        current_list = final_data[key]
        new_movies = categorized[key]
        old_map = {m['slug']: m for m in current_list}
        
        updated_slugs = set()
        list_to_pushed_front = []
        
        for nm in new_movies:
            slug = nm['slug']
            if slug in updated_slugs: continue
            
            if slug in old_map:
                if old_map[slug]['current_episode'] != nm['current_episode']:
                    report_details.append({"cat": key, "name": nm['name'], "type": "🔄 Ghi đè tập mới", "ep": nm['current_episode']})
                list_to_pushed_front.append(nm)
            else:
                report_details.append({"cat": key, "name": nm['name'], "type": "✨ Thêm mới", "ep": nm['current_episode']})
                list_to_pushed_front.append(nm)
                
            updated_slugs.add(slug)
            
        remained_old = [m for m in current_list if m['slug'] not in updated_slugs]
        final_data[key] = (list_to_pushed_front + remained_old)[:MAX_ITEMS_PER_CAT]

    for key, value in final_data.items():
        file_path = os.path.join(OUTPUT_DIR, f"{key}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=4)

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report_details, f, ensure_ascii=False, indent=4)
        
    print(f"🎉 Hoàn thành cập nhật! Có {len(report_details)} thay đổi.")

if __name__ == "__main__":
    main()
