import requests

BASE_URL = "https://phimapi.com/v1/api"

def get_movies(endpoint, target_count=15, params=None):
    results = []
    years = [2026, 2025]
    
    for year in years:
        if len(results) >= target_count:
            break
            
        page = 1
        while len(results) < target_count:
            # Build params
            current_params = params.copy() if params else {}
            current_params.update({'page': page, 'year': year, 'limit': 20})
            
            try:
                response = requests.get(f"{BASE_URL}/{endpoint}", params=current_params).json()
                items = response.get('data', {}).get('items', [])
                if not items:
                    break
                
                for item in items:
                    if len(results) < target_count:
                        # Tránh trùng lặp
                        if item['_id'] not in [x['_id'] for x in results]:
                            results.append(item)
                    else:
                        break
                page += 1
            except:
                break
    return results

def crawl_all():
    all_data = {}
    
    # 1. Phim mới cập nhật (Dùng API riêng theo trang 1 tài liệu)
    all_data['phim_moi'] = get_movies("danh-sach/phim-moi-cap-nhat", 15) # [cite: 5]

    # 2. Phim chiếu rạp
    all_data['chieu_rap'] = get_movies("danh-sach/phim-chieu-rap", 15) # 

    # 3. Anime Movie (API Hoạt hình + lọc số tập là Full/1)
    anime_list = get_movies("danh-sach/hoat-hinh", 50) 
    all_data['anime_movie'] = [m for m in anime_list if str(m.get('episode_total', '')).lower() in ['full', '1', '01']][:15]

    # 4. Anime Nhật Bản (Bộ)
    all_data['anime_nhat'] = get_movies("quoc-gia/nhat-ban", 15, {'category': 'hoat-hinh'}) # [cite: 86]
    # Lọc bỏ movie nếu cần dựa trên logic ep_total != full

    # 5. HH Trung Quốc (Bộ)
    all_data['hh_trung_quoc'] = get_movies("quoc-gia/trung-quoc", 15, {'category': 'hoat-hinh'}) # [cite: 86]

    # Nhóm Phim Lẻ (phim-le) 
    all_data['phim_le'] = get_movies("danh-sach/phim-le", 15)
    all_data['le_vn'] = get_movies("quoc-gia/viet-nam", 15, {'category': 'phim-le'})
    all_data['le_han'] = get_movies("quoc-gia/han-quoc", 15, {'category': 'phim-le'})
    all_data['le_trung'] = get_movies("quoc-gia/trung-quoc", 15, {'category': 'phim-le'})
    all_data['le_thai'] = get_movies("quoc-gia/thanh-lan", 15, {'category': 'phim-le'})
    all_data['le_au_my'] = get_movies("quoc-gia/au-my", 15, {'category': 'phim-le'})

    # Nhóm Phim Bộ (phim-bo) 
    all_data['bo_vn'] = get_movies("quoc-gia/viet-nam", 15, {'category': 'phim-bo'})
    all_data['bo_han'] = get_movies("quoc-gia/han-quoc", 15, {'category': 'phim-bo'})
    all_data['bo_trung'] = get_movies("quoc-gia/trung-quoc", 15, {'category': 'phim-bo'})
    all_data['bo_thai'] = get_movies("quoc-gia/thanh-lan", 15, {'category': 'phim-bo'})
    all_data['bo_au_my'] = get_movies("quoc-gia/au-my", 15, {'category': 'phim-bo'})

    # 17. Top 10 phim bộ (Mix từ kết quả trên)
    all_data['top_10_bo'] = (all_data['bo_trung'][:4] + all_data['bo_han'][:3] + 
                             all_data['bo_au_my'][:2] + all_data['bo_thai'][:1])

    # 18 & 19. Phim Lồng tiếng & Thuyết minh (Tổng hợp từ toàn bộ data đã crawl)
    # Gom tất cả phim đã tìm thấy vào một tập hợp duy nhất
    pool = []
    for key in all_data:
        pool.extend(all_data[key])
    
    # Lọc dựa trên bảng mã ngôn ngữ trong tài liệu [cite: 38, 53, 78]
    all_data['long_tieng'] = [m for m in pool if 'long-tieng' in str(m.get('lang', '')).lower()][:15]
    all_data['thuyet_minh'] = [m for m in pool if 'thuyet-minh' in str(m.get('lang', '')).lower()][:15]

    return all_data

# Thực thi crawl
final_results = crawl_all()
