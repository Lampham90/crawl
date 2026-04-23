import json
import os
from datetime import datetime

OUTPUT_DIR = "data_categories"

def generate_report():
    print("\n" + "="*45)
    print(f"   BÁO CÁO DỮ LIỆU - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("="*45)
    print(f"| {'Hạng mục (File)':22} | {'Số lượng':16} |")
    print("-" * 45)

    if not os.path.exists(OUTPUT_DIR):
        print("⚠️ Thư mục data_categories không tồn tại!")
        return

    # Quét tất cả các file .json trong thư mục
    files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith('.json')])
    
    total_movies = 0
    for filename in files:
        try:
            with open(os.path.join(OUTPUT_DIR, filename), "r", encoding="utf-8") as f:
                data = json.load(f)
                count = len(data)
                total_movies += count
                status = "✅ ĐỦ" if count >= 200 else f"⚠️ {count}/200"
                print(f"| {filename:22} | {status:16} |")
        except:
            print(f"| {filename:22} | ❌ LỖI ĐỌC FILE  |")

    print("="*45)
    print(f"Tổng cộng: {total_movies} phim đã được bào.")
    print("="*45 + "\n")

if __name__ == "__main__":
    generate_report()
