"""
Export điều luật từ MySQL thành prompt sẵn sàng paste vào web AI (ChatGPT/Claude).
Mỗi file = 1 batch chủ đề → paste vào web → copy JSON output → lưu lại.

Cách chạy:
    python scripts/export_for_web.py
    python scripts/export_for_web.py --per-topic 10 --sub-batches 4

Output: thư mục scripts/web_batches/
    batch_01.txt, batch_02.txt, ...  (paste từng file vào web AI)
"""

import sys, os, json, re, argparse, math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUT_DIR       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web_batches")
MIN_PER_TOPIC = 100  # lấy nhiều để sau filter is_meaningful vẫn đủ
BATCH_SIZE    = 1   # số chủ đề mỗi batch (1 chủ đề = 1 file để không quá dài)

PROMPT_HEADER = """\
Tôi có danh sách các điều luật pháp luật Việt Nam dưới đây.
Với MỖI điều luật, hãy tạo 1 câu hỏi tự nhiên bằng ngôn ngữ đời thường mà người dân có thể hỏi khi cần tư vấn pháp lý về nội dung đó.

Yêu cầu:
- Dùng ngôn ngữ đời thường, KHÔNG dùng thuật ngữ pháp lý phức tạp
- Câu hỏi phải hỏi về quyền lợi, nghĩa vụ, mức phạt, điều kiện, thủ tục... cụ thể trong điều luật
- KHÔNG hỏi chung chung kiểu "quy định này có hiệu lực từ ngày nào?" hay "ai chịu trách nhiệm thi hành?"
- Câu hỏi phải có đủ ngữ cảnh để hiểu được khi đọc độc lập (không cần biết tên văn bản)
- Trả về JSON array đúng format sau, KHÔNG giải thích thêm:

[
  {"mapc": "...", "question": "..."},
  {"mapc": "...", "question": "..."}
]

DANH SÁCH ĐIỀU LUẬT:
"""


def strip_html(html: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', html or '')
    return re.sub(r'\s+', ' ', text).strip()


# Tên điều chứa các từ này thường không có nội dung pháp lý thực chất
_SKIP_KEYWORDS = [
    "hiệu lực", "thi hành", "điều khoản chuyển tiếp",
    "tổ chức thực hiện", "trách nhiệm thi hành",
    "điều khoản thi hành", "quy định chuyển tiếp",
]

def is_meaningful(item: dict) -> bool:
    """Bỏ qua các điều về hiệu lực, thi hành, chuyển tiếp — không có ngữ cảnh thực chất."""
    ten = item["dieu_ten"].lower()
    if any(kw in ten for kw in _SKIP_KEYWORDS):
        return False
    if len(item["noidung"]) < 80:   # nội dung quá ngắn
        return False
    return True


def load_from_mysql(per_topic: int) -> dict[str, list]:
    from app.db.database import get_db

    print("Kết nối MySQL...")
    by_topic = {}

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT cd.id, cd.ten AS chu_de, COUNT(*) AS cnt
                FROM pddieu d
                JOIN pdchude cd ON d.chude_id = cd.id
                WHERE d.noidung IS NOT NULL AND d.noidung != ''
                  AND d.ten    IS NOT NULL AND d.ten    != ''
                GROUP BY cd.id, cd.ten
                ORDER BY cd.stt
            """)
            topics = cur.fetchall()

        for topic in topics:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT d.mapc, d.ten AS dieu_ten, d.noidung, cd.ten AS chu_de
                    FROM pddieu d
                    JOIN pdchude cd ON d.chude_id = cd.id
                    WHERE d.chude_id = %s
                      AND d.noidung IS NOT NULL AND d.noidung != ''
                      AND d.ten    IS NOT NULL AND d.ten    != ''
                    ORDER BY RAND()
                    LIMIT %s
                """, (topic['id'], per_topic))
                rows = cur.fetchall()

            items = [
                {
                    "mapc":     str(r["mapc"]),
                    "dieu_ten": str(r["dieu_ten"]).strip(),
                    "noidung":  strip_html(r["noidung"]),
                    "chu_de":   str(r["chu_de"]),
                }
                for r in rows
            ]
            by_topic[topic['chu_de']] = [it for it in items if is_meaningful(it)]

    print(f"Đã load {sum(len(v) for v in by_topic.values())} điều từ {len(by_topic)} chủ đề")
    return by_topic


def build_batch_text(topics_chunk: list[tuple[str, list]]) -> str:
    """Tạo nội dung 1 file batch để paste vào web AI."""
    lines = [PROMPT_HEADER]
    idx = 1
    for chu_de, items in topics_chunk:
        lines.append(f"\n--- Chủ đề: {chu_de} ---")
        for item in items:
            lines.append(
                f"\n[{idx}] mapc={item['mapc']}\n"
                f"Tên: {item['dieu_ten']}\n"
                f"Nội dung: {item['noidung']}"
            )
            idx += 1
    return "\n".join(lines)


def save_metadata(by_topic: dict, out_dir: str):
    """Lưu metadata để merge câu hỏi sau này."""
    meta = {}
    for chu_de, items in by_topic.items():
        for item in items:
            meta[item["mapc"]] = {
                "dieu_ten": item["dieu_ten"],
                "noidung":  item["noidung"],
                "chu_de":   item["chu_de"],
            }
    meta_path = os.path.join(out_dir, "_metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"Lưu metadata: {meta_path}")
    return meta_path


MAX_PER_BATCH = 30   # tối đa số điều mỗi batch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-topic",     type=int, default=MIN_PER_TOPIC,
                        help=f"Số điều mỗi chủ đề (default: {MIN_PER_TOPIC})")
    parser.add_argument("--max-per-batch", type=int, default=MAX_PER_BATCH,
                        help=f"Số điều tối đa mỗi batch (default: {MAX_PER_BATCH})")
    args = parser.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)

    by_topic = load_from_mysql(args.per_topic)

    # Gom tất cả điều (giữ nguyên chu_de) rồi chia theo max_per_batch
    all_items = []
    for chu_de, items in by_topic.items():
        for item in items:
            all_items.append((chu_de, item))

    total = len(all_items)
    chunk_size = args.max_per_batch
    chunks = [all_items[i:i + chunk_size] for i in range(0, total, chunk_size)]

    print(f"\nTổng: {total} điều → {len(chunks)} batch (tối đa {chunk_size} điều/batch)")

    for i, chunk in enumerate(chunks, 1):
        # Nhóm lại theo chu_de để build_batch_text hiển thị header chủ đề
        by_topic_chunk: dict[str, list] = {}
        for chu_de, item in chunk:
            by_topic_chunk.setdefault(chu_de, []).append(item)

        text     = build_batch_text(list(by_topic_chunk.items()))
        filename = os.path.join(OUT_DIR, f"batch_{i:02d}.txt")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(text)

        topics_str = ", ".join(by_topic_chunk.keys())
        print(f"  batch_{i:02d}.txt — {len(chunk)} điều — {topics_str}")

    save_metadata(by_topic, OUT_DIR)

    print(f"""
{'='*55}
HƯỚNG DẪN:
  1. Mở từng file batch_XX.txt trong {OUT_DIR}
  2. Copy toàn bộ nội dung → paste vào ChatGPT/Claude
  3. Copy JSON output → lưu vào file batch_XX_output.json
     trong cùng thư mục {OUT_DIR}
  4. Sau khi xong tất cả batch, chạy:
     python scripts/merge_questions.py
     → tạo benchmark_questions.json
{'='*55}
""")


if __name__ == "__main__":
    main()
