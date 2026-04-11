"""
Export corpus lớn từ MySQL để benchmark sát thực tế hơn.

Corpus = tất cả điều đã có câu hỏi + N điều ngẫu nhiên bổ sung (nhiễu).

Yêu cầu: đã có benchmark_questions.json (chạy merge_questions.py trước)

Cách chạy:
    python scripts/export_corpus.py
    python scripts/export_corpus.py --total 20000
"""

import sys
import os
# --- path setup ---
_SCRIPT    = os.path.abspath(__file__)
_SCRIPTS_DIR = os.path.dirname(_SCRIPT)
BASE_DIR   = os.path.dirname(os.path.dirname(_SCRIPTS_DIR))
sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)
# ---

import sys, os, json, re, argparse

sys.path.insert(0, BASE_DIR)

SCRIPTS_DIR    = _SCRIPTS_DIR
QUESTIONS_PATH = os.path.join(SCRIPTS_DIR, "benchmark_questions.json")
OUT_PATH       = os.path.join(SCRIPTS_DIR, "benchmark_corpus.json")
DEFAULT_TOTAL  = 20000


def strip_html(html: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', html or '')
    return re.sub(r'\s+', ' ', text).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--total", type=int, default=DEFAULT_TOTAL,
                        help=f"Tổng số điều trong corpus (default: {DEFAULT_TOTAL})")
    args = parser.parse_args()

    # Load câu hỏi để lấy danh sách mapc bắt buộc có trong corpus
    if not os.path.exists(QUESTIONS_PATH):
        print("LỖI: Không tìm thấy benchmark_questions.json. Chạy merge_questions.py trước.")
        return

    with open(QUESTIONS_PATH, encoding="utf-8") as f:
        questions = json.load(f)

    required_mapcs = {q["mapc"] for q in questions}
    print(f"Câu hỏi       : {len(questions)}")
    print(f"Điều bắt buộc : {len(required_mapcs)}")

    from app.db.database import get_db

    corpus = []

    with get_db() as conn:
        # 1. Load tất cả điều đã có câu hỏi (bắt buộc có trong corpus)
        print(f"Load {len(required_mapcs)} điều bắt buộc...")
        chunk_size = 500
        required_list = list(required_mapcs)
        for i in range(0, len(required_list), chunk_size):
            chunk = required_list[i:i + chunk_size]
            placeholders = ",".join(["%s"] * len(chunk))
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT d.mapc, d.ten AS dieu_ten, d.noidung, cd.ten AS chu_de
                    FROM pddieu d
                    JOIN pdchude cd ON d.chude_id = cd.id
                    WHERE d.mapc IN ({placeholders})
                """, chunk)
                rows = cur.fetchall()
            for r in rows:
                corpus.append({
                    "mapc":     str(r["mapc"]),
                    "dieu_ten": str(r["dieu_ten"]).strip(),
                    "noidung":  strip_html(r["noidung"])[:600],
                    "chu_de":   str(r["chu_de"]),
                })

        # 2. Load thêm điều ngẫu nhiên (nhiễu) cho đủ total
        need = args.total - len(corpus)
        if need > 0:
            print(f"Load thêm {need} điều ngẫu nhiên (nhiễu)...")
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT d.mapc, d.ten AS dieu_ten, d.noidung, cd.ten AS chu_de
                    FROM pddieu d
                    JOIN pdchude cd ON d.chude_id = cd.id
                    WHERE d.noidung IS NOT NULL AND d.noidung != ''
                      AND d.ten    IS NOT NULL AND d.ten    != ''
                    ORDER BY RAND()
                    LIMIT %s
                """, (need * 2,))  # lấy dư để lọc trùng
                rows = cur.fetchall()

            added = 0
            for r in rows:
                if str(r["mapc"]) not in required_mapcs:
                    corpus.append({
                        "mapc":     str(r["mapc"]),
                        "dieu_ten": str(r["dieu_ten"]).strip(),
                        "noidung":  strip_html(r["noidung"])[:600],
                        "chu_de":   str(r["chu_de"]),
                    })
                    added += 1
                    if added >= need:
                        break

    # Shuffle để câu hỏi không nằm đầu corpus
    import random
    random.shuffle(corpus)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*55}")
    print(f"Corpus size   : {len(corpus)} điều")
    print(f"  Có câu hỏi  : {len(required_mapcs)}")
    print(f"  Nhiễu       : {len(corpus) - len(required_mapcs)}")
    print(f"Lưu tại       : {OUT_PATH}")
    print(f"\nUpload 2 file lên Drive:")
    print(f"  - benchmark_questions.json")
    print(f"  - benchmark_corpus.json")
    print(f"{'='*55}")


if __name__ == "__main__":
    main()
