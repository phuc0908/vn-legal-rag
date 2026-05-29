"""
Ingest dữ liệu chủ đề Hôn nhân & Gia đình vào ChromaDB riêng.

Nguồn dữ liệu:
  1. Đề mục "Hôn nhân và gia đình" (demuc_id: 4913a1cf-...)
     → Luật HN&GĐ 52/2014 + các Nghị định, Thông tư hướng dẫn
  2. Chương XVII BLHS — "Các Tội xâm phạm chế độ hôn nhân và gia đình"
     (chuong_id: 1600100000000000200001700000000000000000)
     → Điều 181–187 Bộ luật Hình sự 2015 sửa đổi 2017

Mỗi điều được split thành các khoản (chunk).
Mỗi chunk có dạng:
    Chủ đề: ... | Đề mục: ... | Chương: ...
    Điều <so>. <ten dieu>
    <noi dung khoan>
    Văn bản: <vbqppl>

Usage:
    python scripts/ingest_hon_nhan.py                  # ingest vào chroma_db_hon_nhan/
    python scripts/ingest_hon_nhan.py --preview        # in mẫu 10 chunk đầu, không embed
    python scripts/ingest_hon_nhan.py --export-json    # export JSON để embed trên Colab
    python scripts/ingest_hon_nhan.py --reset          # xóa chroma_db_hon_nhan/ trước khi ingest
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

import sys
import os
import re
import time
import json

sys.path.insert(0, BASE_DIR)

from app.db.database import get_db

# ── Hằng số nguồn dữ liệu ────────────────────────────────────────────────────
DEMUC_HNGD_ID       = "4913a1cf-5f78-471c-a807-ed5f8c57aaee"   # Hôn nhân và gia đình
CHUONG_XVII_HS_MAPC = "1600100000000000200001700000000000000000" # Chương XVII BLHS

CHROMA_PATH = os.path.join(
    BASE_DIR,
    "chroma_db_hon_nhan",
)
BM25_PATH = os.path.join(
    BASE_DIR,
    "bm25_hon_nhan.pkl",
)
EXPORT_PATH = os.path.join(
    _SCRIPTS_DIR,
    "hon_nhan_export.json",
)

BATCH_SIZE = 100


# ── Logging ───────────────────────────────────────────────────────────────────

def log(msg: str):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ── SQL ───────────────────────────────────────────────────────────────────────

FETCH_SQL = """
    SELECT
        d.mapc,
        d.ten          AS dieu_ten,
        d.chimuc       AS dieu_so,
        d.noidung,
        d.vbqppl,
        cd.id          AS chu_de_id,
        cd.ten         AS chu_de,
        dm.ten         AS de_muc,
        c.ten          AS chuong_ten,
        c.chimuc       AS chuong_so
    FROM pddieu d
    JOIN pdchude  cd ON d.chude_id  = cd.id
    JOIN pddemuc  dm ON d.demuc_id  = dm.id
    LEFT JOIN pdchuong c  ON d.chuong_id = c.mapc
    WHERE
        d.noidung IS NOT NULL AND d.noidung != ''
        AND (d.muc_id IS NULL OR d.muc_id != d.mapc)
        AND (
            d.demuc_id  = %s
            OR d.chuong_id = %s
        )
    ORDER BY cd.stt, dm.stt, c.stt, d.stt
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def strip_html(html: str) -> str:
    """Xóa thẻ HTML, chuẩn hóa khoảng trắng."""
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", text).strip()


def split_khoans(noidung: str) -> list[str]:
    """
    Tách noidung thành danh sách khoản.
    Khoản bắt đầu bằng số nguyên + dấu chấm + khoảng trắng ở đầu từ.
    Nếu không có nhiều khoản → trả về [noidung].
    """
    positions = [m.start() for m in re.finditer(r"(?<![0-9])(\d+)\. ", noidung)]
    if len(positions) < 2:
        return [noidung]
    parts = []
    for i, pos in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(noidung)
        parts.append(noidung[pos:end].strip())
    return parts


def build_header(row: dict) -> str:
    parts = []
    if row.get("chu_de"):
        parts.append(f"Chủ đề: {row['chu_de']}")
    if row.get("de_muc"):
        parts.append(f"Đề mục: {row['de_muc']}")
    if row.get("chuong_ten"):
        parts.append(f"Chương: {row['chuong_ten']}")
    return " | ".join(parts)


def build_metadata(row: dict) -> dict:
    return {
        "dieu_mapc":  str(row["mapc"]),
        "dieu_ten":   str(row["dieu_ten"] or ""),
        "dieu_so":    str(row["dieu_so"] or ""),
        "chu_de_id":  str(row["chu_de_id"]),
        "chu_de":     str(row["chu_de"] or ""),
        "de_muc":     str(row["de_muc"] or ""),
        "chuong_ten": str(row.get("chuong_ten") or ""),
        "module":     "hon_nhan",
    }


def make_chunks(row: dict) -> list[dict]:
    """
    Tạo 1 hoặc nhiều chunk từ 1 điều.

    Mỗi chunk:
      - id      : pddieu_<mapc>  hoặc  pddieu_<mapc>_k<n>  (nếu có nhiều khoản)
      - content : header + tên điều + nội dung khoản [+ văn bản]
      - metadata: dict đầy đủ

    Tên điều luật luôn xuất hiện trong mỗi chunk để đảm bảo ngữ cảnh
    khi retrieve từng khoản riêng lẻ.
    """
    noidung  = strip_html(row.get("noidung", ""))
    header   = build_header(row)
    dieu_ten = str(row.get("dieu_ten") or "")
    vbqppl   = str(row.get("vbqppl") or "")
    metadata = build_metadata(row)
    khoans   = split_khoans(noidung)

    def _make_content(khoan_text: str) -> str:
        parts = [p for p in [header, dieu_ten, khoan_text] if p]
        if vbqppl:
            parts.append(f"Văn bản: {vbqppl}")
        return "\n".join(parts)

    if len(khoans) == 1:
        content = _make_content(noidung)
        if not content.strip():
            return []
        return [{"id": f"pddieu_{row['mapc']}", "content": content, "metadata": metadata}]

    chunks = []
    for i, khoan_text in enumerate(khoans, 1):
        content = _make_content(khoan_text)
        if content.strip():
            chunks.append({
                "id":       f"pddieu_{row['mapc']}_k{i}",
                "content":  content,
                "metadata": metadata,
            })
    return chunks


# ── Fetch ─────────────────────────────────────────────────────────────────────

def fetch_rows(conn) -> list:
    log("Đang tải dữ liệu từ MySQL...")
    with conn.cursor() as cur:
        cur.execute(FETCH_SQL, (DEMUC_HNGD_ID, CHUONG_XVII_HS_MAPC))
        rows = cur.fetchall()

    from collections import Counter
    sources = Counter(r["de_muc"] for r in rows)
    log(f"  Tổng: {len(rows)} điều từ {len(sources)} nguồn:")
    for src, cnt in sources.items():
        log(f"    • {src}: {cnt} điều")
    return rows


def build_all_chunks(rows: list) -> list[dict]:
    all_chunks = []
    for r in rows:
        all_chunks.extend(make_chunks(dict(r)))
    log(f"  {len(rows)} điều → {len(all_chunks)} chunks")
    return all_chunks


# ── Preview ───────────────────────────────────────────────────────────────────

def preview(chunks: list[dict], n: int = 10):
    print("=" * 70)
    print(f"PREVIEW — {n} chunk đầu (tổng {len(chunks)} chunks)")
    print("=" * 70)
    for i, c in enumerate(chunks[:n]):
        print(f"\n── Chunk {i+1} ── id: {c['id']}")
        print(c["content"][:400])
        if len(c["content"]) > 400:
            print("  ...")
    print("=" * 70)


# ── Export JSON ───────────────────────────────────────────────────────────────

def export_json(chunks: list[dict]):
    with open(EXPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False)
    size_mb = os.path.getsize(EXPORT_PATH) / 1024 / 1024
    log(f"Exported {len(chunks)} chunks → {EXPORT_PATH} ({size_mb:.2f} MB)")
    log("Upload file này lên Google Colab để embed với GPU.")


# ── Ingest ────────────────────────────────────────────────────────────────────

def ingest(chunks: list[dict]):
    """Embed và lưu vào chroma_db_hon_nhan/."""
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import Chroma
    from app.core.config import settings

    log(f"Khởi tạo embedding model: {settings.EMBEDDING_MODEL}")
    embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)

    log(f"Khởi tạo ChromaDB tại: {CHROMA_PATH}")
    vectorstore = Chroma(
        embedding_function=embeddings,
        persist_directory=CHROMA_PATH,
    )

    total = len(chunks)
    t_start = time.time()

    for batch_start in range(0, total, BATCH_SIZE):
        batch = chunks[batch_start: batch_start + BATCH_SIZE]
        batch_idx = batch_start // BATCH_SIZE + 1
        t_batch = time.time()

        vectorstore.add_texts(
            texts=[c["content"] for c in batch],
            metadatas=[c["metadata"] for c in batch],
            ids=[c["id"] for c in batch],
        )

        done = min(batch_start + BATCH_SIZE, total)
        elapsed = time.time() - t_start
        speed = done / elapsed if elapsed > 0 else 0
        eta = (total - done) / speed if speed > 0 else 0
        log(
            f"  Batch {batch_idx}: {len(batch)} chunks | "
            f"[{done}/{total}] {done/total*100:.1f}% | "
            f"batch={time.time()-t_batch:.1f}s | ETA={eta:.0f}s"
        )

    log(f"Hoàn tất embed: {total} chunks sau {time.time()-t_start:.1f}s")


# ── Build BM25 ────────────────────────────────────────────────────────────────

def build_bm25(chunks: list[dict]):
    """Build và save BM25 index riêng cho module hôn nhân."""
    from app.rag.retrieval import BM25Index

    log(f"Đang build BM25 index ({len(chunks)} chunks)...")
    bm25 = BM25Index(index_path=BM25_PATH)
    bm25.build(chunks)
    bm25.save()
    log(f"BM25 index đã lưu: {BM25_PATH}")


# ── Reset ─────────────────────────────────────────────────────────────────────

def reset_chroma():
    import shutil
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)
        log(f"Đã xóa: {CHROMA_PATH}")
    else:
        log("chroma_db_hon_nhan/ chưa tồn tại, bỏ qua.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    do_reset    = "--reset" in sys.argv
    do_preview  = "--preview" in sys.argv
    do_export   = "--export-json" in sys.argv
    do_bm25     = "--bm25-only" in sys.argv

    print("=" * 60)
    log("Ingest Module: Hôn nhân & Gia đình")
    log(f"  ChromaDB path : {CHROMA_PATH}")
    log(f"  BM25 path     : {BM25_PATH}")
    print("=" * 60)

    if do_reset:
        reset_chroma()

    log("Kết nối MySQL...")
    with get_db() as conn:
        rows = fetch_rows(conn)

    chunks = build_all_chunks(rows)

    if do_preview:
        preview(chunks, n=10)
        return

    if do_export:
        export_json(chunks)
        return

    if do_bm25:
        build_bm25(chunks)
        return

    # Full ingest
    print()
    ans = input("Tiến hành embed vào chroma_db_hon_nhan/? (y/n): ").strip().lower()
    if ans != "y":
        log("Hủy.")
        return

    ingest(chunks)

    print()
    ans2 = input("Build BM25 index (bm25_hon_nhan.pkl)? (y/n): ").strip().lower()
    if ans2 == "y":
        build_bm25(chunks)

    print("=" * 60)
    log(f"DONE — module hon_nhan sẵn sàng.")
    print("=" * 60)


if __name__ == "__main__":
    main()
