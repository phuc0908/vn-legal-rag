"""
Ingest bảng vb_chimuc từ MySQL vào ChromaDB.
Mỗi row trong vb_chimuc = 1 vector (không split thêm).

Metadata mỗi vector:
  - id_vb       : FK → vbpl.id (ID văn bản pháp luật)
  - chi_muc_cha : ID chương cha (null nếu row là chương)

Usage:
    python scripts/ingest_from_db.py           # ingest toàn bộ
    python scripts/ingest_from_db.py --reset   # xóa ChromaDB cũ rồi ingest

Lưu ý: Nếu ChromaDB đã có dữ liệu và không dùng --reset,
        script sẽ báo lỗi duplicate ID. Dùng --reset để ingest lại từ đầu.
"""

import sys
import os
import time

# Cho phép import từ thư mục backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import get_db
from app.rag.retrieval import get_rag_system

BATCH_SIZE = 500


def fetch_batches(conn):
    """Đọc toàn bộ vb_chimuc theo batch để tránh load hết vào RAM."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) as cnt FROM vb_chimuc WHERE noi_dung IS NOT NULL AND noi_dung != ''")
        total = cur.fetchone()["cnt"]

    print(f"  Tổng rows có nội dung: {total}")

    offset = 0
    while offset < total:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, id_vb, noi_dung, chi_muc_cha FROM vb_chimuc "
                "WHERE noi_dung IS NOT NULL AND noi_dung != '' "
                "ORDER BY id LIMIT %s OFFSET %s",
                (BATCH_SIZE, offset),
            )
            rows = cur.fetchall()
        if not rows:
            break
        yield rows, total
        offset += len(rows)


def reset_chroma():
    """Xóa toàn bộ dữ liệu trong ChromaDB."""
    import shutil
    chroma_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma_db")
    if os.path.exists(chroma_path):
        shutil.rmtree(chroma_path)
        print(f"  Đã xóa: {chroma_path}")
    else:
        print(f"  Không tìm thấy {chroma_path}, bỏ qua.")


def main():
    do_reset = "--reset" in sys.argv

    if do_reset:
        print("[0/3] Reset ChromaDB...")
        reset_chroma()

    print("[1/3] Kết nối DB và đếm rows...")
    t_start = time.time()

    with get_db() as conn:
        print("[2/3] Khởi tạo RAG system (load embedding model)...")
        t0 = time.time()
        rag = get_rag_system()
        print(f"      Xong sau {time.time() - t0:.1f}s")

        print(f"[3/3] Embed và lưu vào ChromaDB (batch={BATCH_SIZE})...")
        total_ingested = 0

        for batch, total in fetch_batches(conn):
            rows_to_add = [
                {
                    "id":       f"vb_chimuc_{row['id']}",
                    "content":  row["noi_dung"],
                    "metadata": {
                        "id_vb":       row["id_vb"],
                        "chi_muc_cha": row["chi_muc_cha"],
                    },
                }
                for row in batch
            ]

            rag.add_documents_direct(rows_to_add)
            total_ingested += len(rows_to_add)

            pct = total_ingested / total * 100
            elapsed = time.time() - t_start
            print(f"  [{total_ingested}/{total}] {pct:.1f}% — {elapsed:.1f}s")

    print(f"\n[DONE] Đã index {total_ingested} vectors vào ChromaDB ({time.time() - t_start:.1f}s tổng).")


if __name__ == "__main__":
    main()
