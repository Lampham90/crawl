import requests
import json
import time

# Endpoint chuẩn dựa trên tài liệu theo năm
BASE_URL = "https://phimapi.com/v1/api/nam"
YEARS = [2026, 2025]
TARGET = 2 # Test mỗi loại 2 phim theo ý m

def fetch_and_parse(target_name, year, params):
    url = f"{BASE_URL}/{year}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # Tham số lọc từ API
    query_params = {"page": 1, "limit": 64}
    query_params.update(params)
    
    try:
        res = requests.get(url, params=query_params, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            # API trả về danh sách phim trong data['items']
            items = data.get('data', {}).get('items', [])
            
            results = []
            for item in items[:20]: # Quét nhanh 20 phim đầu để lọc
                if len(results) >= TARGET: break
                
                # Gọi chi tiết để lấy đúng cấu trúc JSON m gửi
                d_res = requests.get(f"https://phimapi.com/phim/{item['slug']}")
                if d_res.status_code != 200: continue
                
                detail = d_res.json()
                m = detail.get('movie', {})
                if not m: continue

                # --- XỬ LÝ JSON THỰC TẾ ---
                # Lấy tên quốc gia (đọc từ mảng object)
                countries = [c.get('name') for c in m.get('country', [])]
                # Lấy thể loại
                categories = [cat.get('slug') for cat in m.get('category', [])]
                
                # Biến kiểm tra
                ep_total = str(m.get('episode_total', '1'))
                m_type = m.get('type', '') # 'series' hoặc 'single'

                # Logic phân loại đơn giản
                is_match = False
                if target_name == "ANIME NHẬT" and "hoat-hinh" in categories and "Chile" not in countries: # Chile là ví dụ từ JSON m gửi
                     if "Nhật Bản" in countries: is_match = True
                elif target_name == "HH TRUNG QUỐC" and "hoat-hinh" in categories and "Trung Quốc" in countries:
                    is_match = True
                elif "PHIM BỘ" in target_name and m_type == "series":
                    is_match = True
                elif "PHIM LẺ" in target_name and m_type == "single":
                    is_match = True
                else:
                    # Nếu không gán gì thì lấy đại diện để test kết nối
                    is_match = True

                if is_match:
                    results.append(m.get('name'))
                    print(f"  + [{target_name}]: {m.get('name')} ({m.get('year')})")
            
            return results
    except Exception as e:
        print(f"Lỗi: {e}")
    return []

def main():
    print("--- TEST LỌC THEO JSON THỰC TẾ ---")
    
    for y in YEARS:
        print(f"\n--- NĂM {y} ---")
        # 1. Anime & Hoạt hình
        fetch_and_parse("ANIME NHẬT", y, {"category": "hoat-hinh", "country": "nhat-ban"})
        fetch_and_parse("HH TRUNG QUỐC", y, {"category": "hoat-hinh", "country": "trung-quoc"})

        # 2. Quốc gia (Việt, Hàn, Trung, Âu Mỹ, Thái)
        mapping = [
            ("viet-nam", "VIỆT NAM"), ("han-quoc", "HÀN QUỐC"), 
            ("trung-quoc", "TRUNG QUỐC"), ("au-my", "ÂU MỸ"), ("thanh-lan", "THÁI LAN")
        ]
        
        for c_slug, c_name in mapping:
            fetch_and_parse(f"PHIM LẺ {c_name}", y, {"category": "phim-le", "country": c_slug})
            fetch_and_parse(f"PHIM BỘ {c_name}", y, {"category": "phim-bo", "country": c_slug})

    print("\n--- HOÀN TẤT ---")

if __name__ == "__main__":
    main()
