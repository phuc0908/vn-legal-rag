import os
import json

# Lấy thư mục chứa file .py
base_dir = _SCRIPTS_DIR

# web_batches nằm trong scripts
output_dir = os.path.join(base_dir, "web_batches")
os.makedirs(output_dir, exist_ok=True)

for i in range(1, 123):
    filename = f"batch_{i:02d}_output.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)

print("Đã tạo xong file JSON trong scripts/web_batches.")