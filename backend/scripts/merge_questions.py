"""
Merge tất cả batch_XX_output.json thành benchmark_questions.json.

Cách chạy:
    python scripts/merge_questions.py
"""

import os, json, re, glob

BATCHES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web_batches")
OUT_PATH    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "benchmark_questions.json")


def main():
    # Load metadata
    meta_path = os.path.join(BATCHES_DIR, "_metadata.json")
    if not os.path.exists(meta_path):
        print("LỖI: Không tìm thấy _metadata.json. Chạy export_for_web.py trước.")
        return

    with open(meta_path, encoding="utf-8") as f:
        metadata = json.load(f)
    print(f"Metadata: {len(metadata)} điều")

    # Load tất cả output file
    output_files = sorted(glob.glob(os.path.join(BATCHES_DIR, "batch_*_output.json")))
    if not output_files:
        print(f"LỖI: Không tìm thấy file batch_XX_output.json trong {BATCHES_DIR}")
        return

    print(f"Tìm thấy {len(output_files)} output file")

    results = []
    errors  = 0

    for fpath in output_files:
        fname = os.path.basename(fpath)
        try:
            with open(fpath, encoding="utf-8") as f:
                content = f.read().strip()

            # Tự động extract JSON array nếu AI trả về thêm text thừa
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if not match:
                print(f"  ⚠ {fname}: không tìm thấy JSON array, bỏ qua")
                errors += 1
                continue

            items = json.loads(match.group())

            for item in items:
                mapc = str(item.get("mapc", "")).strip()
                question = str(item.get("question", "")).strip()

                if not mapc or not question:
                    errors += 1
                    continue

                if mapc not in metadata:
                    print(f"  ⚠ mapc {mapc} không có trong metadata, bỏ qua")
                    errors += 1
                    continue

                meta = metadata[mapc]
                results.append({
                    "question": question,
                    "dieu_ten": meta["dieu_ten"],
                    "noidung":  meta["noidung"],
                    "chu_de":   meta["chu_de"],
                    "mapc":     mapc,
                })

            print(f"  {fname}: {len(items)} câu hỏi")

        except Exception as e:
            print(f"  ⚠ {fname}: LỖI — {e}")
            errors += 1

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"Tổng: {len(results)} câu hỏi ({errors} lỗi)")
    print(f"Lưu: {OUT_PATH}")

    by_cd = {}
    for r in results:
        by_cd[r["chu_de"]] = by_cd.get(r["chu_de"], 0) + 1
    print(f"\nPhân bố ({len(by_cd)} chủ đề):")
    for cd, cnt in sorted(by_cd.items(), key=lambda x: -x[1]):
        print(f"  {cd}: {cnt} câu")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
