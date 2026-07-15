def crawl_universal(display_name, filename, cat_slug=None, lang=None):
    results, seen = [], set()
    print(f"\n>>> Đang cào {display_name}...")
    
    # Mở rộng dải năm đến 1990
    years = range(2026, 1989, -1) 
    
    for year in years:
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
            
            # Nếu API lỗi hoặc không trả về danh sách phim -> Hết dữ liệu năm này
            if not data or 'data' not in data or not data['data'].get('items'):
                print(f"    - Hết dữ liệu năm {year} tại trang {page-1}")
                break
            
            items = data['data']['items']
            if not items: # Kiểm tra danh sách rỗng
                break
                
            process_and_add(items, results, seen)
            
            # Tăng trang để quét tiếp
            page += 1
            # Nghỉ một chút để tránh bị API chặn
            time.sleep(0.8) 
            
    save_data(results, filename)
    return len(results)
