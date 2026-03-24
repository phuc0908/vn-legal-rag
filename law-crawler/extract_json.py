"""
Trích xuất dữ liệu từ jsonData.js (Bộ Pháp Điển Điện Tử) thành các file JSON riêng.
Tạo cấu trúc thư mục phap-dien/ với:
  - chude.json
  - demuc.json
  - treeNode.json
  - demuc/ (copy từ BoPhapDienDienTu/demuc/)
"""

import re
import json
import os
import shutil

SRC_JS = "./BoPhapDienDienTu/jsonData.js"
SRC_DEMUC_DIR = "./BoPhapDienDienTu/demuc"
OUT_DIR = "./phap-dien"

os.makedirs(OUT_DIR, exist_ok=True)

print("Đọc jsonData.js ...")
with open(SRC_JS, "r", encoding="utf-8-sig") as f:
    content = f.read()

def extract_var(content, var_name):
    """Trích xuất giá trị mảng/object của biến JS."""
    pattern = rf"var {var_name}\s*=\s*"
    match = re.search(pattern, content)
    if not match:
        raise ValueError(f"Không tìm thấy biến {var_name}")
    start = match.end()
    # Tìm dấu kết thúc: dấu ; hoặc \nvar tiếp theo
    # Dùng cách đếm dấu ngoặc để tìm điểm kết thúc mảng/object
    bracket = content[start]
    if bracket == '[':
        close = ']'
    elif bracket == '{':
        close = '}'
    else:
        raise ValueError(f"Không xác định được kiểu dữ liệu của {var_name}")

    depth = 0
    end = start
    in_string = False
    escape = False
    string_char = None
    for i, ch in enumerate(content[start:], start):
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if in_string:
            if ch == string_char:
                in_string = False
            continue
        if ch in ('"', "'"):
            in_string = True
            string_char = ch
            continue
        if ch == bracket:
            depth += 1
        elif ch == close:
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    json_str = content[start:end]
    return json.loads(json_str)

# Trích xuất từng biến
for var_name, file_name in [("jdChuDe", "chude.json"), ("jdDeMuc", "demuc.json"), ("jdAllTree", "treeNode.json")]:
    print(f"Trích xuất {var_name} -> {file_name} ...")
    data = extract_var(content, var_name)
    out_path = os.path.join(OUT_DIR, file_name)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Đã lưu {len(data)} mục vào {out_path}")

# Copy thư mục demuc HTML
out_demuc = os.path.join(OUT_DIR, "demuc")
if os.path.exists(out_demuc):
    print(f"Thư mục {out_demuc} đã tồn tại, bỏ qua copy.")
else:
    print(f"Copy {SRC_DEMUC_DIR} -> {out_demuc} ...")
    shutil.copytree(SRC_DEMUC_DIR, out_demuc)
    count = len(os.listdir(out_demuc))
    print(f"  Đã copy {count} file HTML.")

print("Xong! Cấu trúc phap-dien/:")
for item in sorted(os.listdir(OUT_DIR)):
    print(f"  {item}")
