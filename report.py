import json
import os
import sys
from datetime import datetime

OUTPUT_DIR = "data_categories"

def generate_report(target_files=None):
    print("\n" + "="*45)
    print(f"   BÁO CÁO DỮ LIỆU - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("="*45)
    print(f"| {'Hạng mục (File)':22} | {'Số lượng':16} |")
    print("-" * 45)

    if not os.path.exists(OUTPUT_DIR):
        print("⚠️ Thư mục data_categories không tồn tại!")
        return

    # Nếu không truyền danh sách file, nó sẽ lấy hết (như cũ)
    # Nếu có truyền, nó chỉ lấy đúng những file đó
    if target_files:
        files = [f + ".json" if not f.endswith(".json") else f for f in target_files]
    else:
        files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith('.json')])
    
    total_movies = 0
    for filename in files:
        file_path = os.path.join(OUTPUT_DIR, filename)
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    count = len(data)
                    total_movies += count
                    status = "✅ ĐỦ" if count >= 200 else f"⚠️ {count}/200"
                    print(f"| {filename:22} | {status:16} |")
            except:
                print(f"| {filename:22} | ❌ LỖI ĐỌC FILE  |")
        else:
            print(f"| {filename:22} | ⚪ CHƯA CÓ FILE |")

    print("="*45)
    print(f"Tổng cộng: {total_movies} phim trong đợt này.")
    print("="*45 + "\n")

if __name__ == "__main__":
    # Lấy danh sách file từ tham số dòng lệnh
    args = sys.argv[1:]
    generate_report(args if args else None)
