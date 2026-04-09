"""
Build BM25 index từ MySQL pddieu table và lưu ra file pickle.

Cần chạy 1 lần trước khi start server với HYBRID_SEARCH_ENABLED=True.
Chạy lại sau khi data trong MySQL thay đổi.

Usage:
    python scripts/build_bm25_index.py           # Build nếu file chưa tồn tại
    python scripts/build_bm25_index.py --reset   # Force rebuild dù file đã có
"""

import sys
import os
import re
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import get_db
from app.core.config import settings
from app.rag.retrieval import BM25Index


def _strip_html(html: str) -> str:
    """Xóa thẻ HTML, chuẩn hóa whitespace."""
    text = re.sub(r'<[^>]+>', ' ', html or '')
    return re.sub(r'\s+', ' ', text).strip()


def _split_khoans(noidung: str) -> list:
    """Tách nội dung điều thành các khoản (1. 2. 3. ...). Nếu < 2 khoản thì giữ nguyên."""
    positions = [m.start() for m in re.finditer(r'(?<!\S)(\d+)\. ', noidung)]
    if len(positions) < 2:
        return [noidung]
    parts = []
    for i, pos in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(noidung)
        parts.append(noidung[pos:end].strip())
    return parts


def fetch_documents() -> list:
    """Fetch toàn bộ pddieu JOIN với metadata từ MySQL, tách theo khoản nếu có."""
    sql = """
        SELECT
            d.mapc         AS mapc,
            d.ten          AS tieu_de,
            d.noidung      AS noidung,
            c.ten          AS chu_de,
            c.id           AS chu_de_id,
            dm.ten         AS de_muc,
            ch.ten         AS chuong_ten
        FROM pddieu d
        LEFT JOIN pdchude  c  ON d.chude_id  = c.id
        LEFT JOIN pddemuc  dm ON d.demuc_id  = dm.id
        LEFT JOIN pdchuong ch ON d.chuong_id = ch.mapc
        ORDER BY c.stt, dm.stt, ch.mapc, d.stt
    """
    print("[BM25] Đang query MySQL...")
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    docs = []
    for row in rows:
        header_parts = []
        if row.get("chu_de"):     header_parts.append(f"Chủ đề: {row['chu_de']}")
        if row.get("de_muc"):     header_parts.append(f"Đề mục: {row['de_muc']}")
        if row.get("chuong_ten"): header_parts.append(f"Chương: {row['chuong_ten']}")
        header = " | ".join(header_parts)
        tieu_de = str(row.get("tieu_de") or "")
        noidung = _strip_html(row.get("noidung") or "")

        metadata_base = {
            "dieu_mapc":  row["mapc"],
            "chu_de":     row.get("chu_de", ""),
            "chu_de_id":  str(row.get("chu_de_id", "")),
            "de_muc":     row.get("de_muc", ""),
            "chuong_ten": row.get("chuong_ten", ""),
            "tieu_de":    tieu_de,
        }

        khoans = _split_khoans(noidung)
        if len(khoans) == 1:
            content = "\n".join(p for p in [header, tieu_de, noidung] if p)
            docs.append({"id": row["mapc"], "content": content, "metadata": metadata_base})
        else:
            for i, khoan_text in enumerate(khoans, 1):
                content = "\n".join(p for p in [header, tieu_de, khoan_text] if p)
                docs.append({
                    "id":       f"{row['mapc']}_k{i}",
                    "content":  content,
                    "metadata": metadata_base,
                })
    return docs


def main():
    parser = argparse.ArgumentParser(description="Build BM25 index từ MySQL")
    parser.add_argument("--reset", action="store_true", help="Force rebuild dù file đã tồn tại")
    args = parser.parse_args()

    index_path = settings.BM25_INDEX_PATH

    if not args.reset and os.path.exists(index_path):
        size_mb = os.path.getsize(index_path) / 1024 / 1024
        print(f"[BM25] Index đã tồn tại tại '{index_path}' ({size_mb:.1f} MB).")
        print("[BM25] Dùng --reset để rebuild.")
        return

    t_start = time.time()

    docs = fetch_documents()
    print(f"[BM25] Loaded {len(docs)} documents từ MySQL ({time.time()-t_start:.1f}s)")

    print("[BM25] Đang tokenize và build BM25Okapi index...")
    t_build = time.time()
    bm25 = BM25Index(index_path)
    bm25.build(docs)
    print(f"[BM25] Build xong sau {time.time()-t_build:.1f}s")

    print(f"[BM25] Đang lưu ra '{index_path}'...")
    bm25.save()

    total = time.time() - t_start
    size_mb = os.path.getsize(index_path) / 1024 / 1024
    print(f"[BM25] Hoàn tất! {len(docs)} docs | {size_mb:.1f} MB | {total:.1f}s tổng cộng")


if __name__ == "__main__":
    main()
