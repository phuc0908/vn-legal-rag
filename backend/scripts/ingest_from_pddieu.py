"""
Ingest bảng pddieu từ MySQL vào ChromaDB.
Mỗi row trong pddieu = 1 vector.

Join với các bảng liên quan để lấy tên thay vì ID:
  - pdchude  (chude_id)  → chu_de    (tên chủ đề)
  - pddemuc  (demuc_id)  → de_muc    (tên đề mục)
  - pdchuong (chuong_id) → chuong_ten (tên chương)

Nội dung mỗi vector:
  [Header: Chủ đề | Đề mục | Chương]

Metadata mỗi vector:
  - dieu_mapc   : mã pháp điển của điều (vd: "HNGD.1.1.1.1")
  - dieu_ten    : tên điều
  - chu_de_id   : ID chủ đề — dùng để filter ChromaDB theo chủ đề
  - chu_de      : tên chủ đề (vd: "Hôn nhân và Gia đình")
  - de_muc      : tên đề mục
  - chuong_ten  : tên chương


Usage:
    python scripts/ingest_from_pddieu.py                    # ingest toàn bộ
    python scripts/ingest_from_pddieu.py --reset            # xóa ChromaDB cũ rồi ingest
    python scripts/ingest_from_pddieu.py --preview-only     # chỉ tạo file preview JSON, không embed
    python scripts/ingest_from_pddieu.py --chude-id 5       # chỉ ingest chủ đề có id=5
    python scripts/ingest_from_pddieu.py --export-json      # export dữ liệu ra JSON (để embed trên Colab)
"""

import sys
import os
import re
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import get_db

BATCH_SIZE = 200
PREVIEW_LIMIT = 20
PREVIEW_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pddieu_preview.json")
EXPORT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pddieu_export.json")


# ── Helpers ────────────────────────────────────────────────────────────────────

def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def reset_chroma():
    import shutil
    chroma_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma_db"
    )
    if os.path.exists(chroma_path):
        shutil.rmtree(chroma_path)
        log(f"Đã xóa ChromaDB: {chroma_path}")
    else:
        log("ChromaDB chưa tồn tại, bỏ qua bước reset.")


def _strip_html(html: str) -> str:
    """Xóa toàn bộ thẻ HTML, chuẩn hóa khoảng trắng."""
    text = re.sub(r'<[^>]+>', ' ', html or '')
    return re.sub(r'\s+', ' ', text).strip()



# ── Fetch pddieu với JOIN ─────────────────────────────────────────────────────

def fetch_pddieu_rows(conn, chude_id: str = None) -> list:
    """
    Fetch tất cả pddieu rows, join với pdchude, pddemuc, pdchuong
    để lấy tên thay vì chỉ lưu ID.
    """
    log("Đang tải dữ liệu từ pddieu (JOIN pdchude, pddemuc, pdchuong)...")
    sql = """
        SELECT
            d.mapc,
            d.ten          AS dieu_ten,
            d.noidung,
            d.vbqppl,
            d.vbqppl_link,
            d.stt,
            cd.id          AS chu_de_id,
            cd.ten         AS chu_de,
            dm.ten         AS de_muc,
            c.ten          AS chuong_ten
        FROM pddieu d
        JOIN pdchude  cd ON d.chude_id = cd.id
        JOIN pddemuc  dm ON d.demuc_id = dm.id
        LEFT JOIN pdchuong c ON d.chuong_id = c.mapc
        WHERE d.noidung IS NOT NULL AND d.noidung != ''
    """
    if chude_id:
        sql += " AND d.chude_id = %s ORDER BY cd.stt, dm.stt, c.stt, d.stt"
        with conn.cursor() as cur:
            cur.execute(sql, (chude_id,))
            rows = cur.fetchall()
    else:
        sql += " ORDER BY cd.stt, dm.stt, c.stt, d.stt"
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    log(f"  Đã tải {len(rows)} rows từ pddieu")
    return rows


# ── Xây dựng nội dung text cho mỗi vector ────────────────────────────────────

def build_content(row: dict) -> str:
    parts = []

    header_parts = []
    if row.get('chu_de'):
        header_parts.append(f"Chủ đề: {row['chu_de']}")
    if row.get('de_muc'):
        header_parts.append(f"Đề mục: {row['de_muc']}")
    if row.get('chuong_ten'):
        header_parts.append(f"Chương: {row['chuong_ten']}")
    if header_parts:
        parts.append(" | ".join(header_parts))

    if row.get('dieu_ten'):
        parts.append(str(row['dieu_ten']))

    noidung = _strip_html(row.get('noidung', ''))
    if noidung:
        parts.append(noidung)

    if row.get('vbqppl'):
        parts.append(f"Văn bản: {row['vbqppl']}")

    return "\n".join(parts)


# ── Preview ────────────────────────────────────────────────────────────────────

def build_preview(conn, chude_id: str = None):
    """
    Tạo preview dữ liệu trước khi ingest.
    Trả về (preview_dict, rows, tables_map).
    """
    log("Đang tạo preview dữ liệu...")
    rows = fetch_pddieu_rows(conn, chude_id)

    total = len(rows)

    chude_stats = {}
    for r in rows:
        cd = r['chu_de']
        chude_stats[cd] = chude_stats.get(cd, 0) + 1

    content_lens = [len(build_content(dict(r))) for r in rows]

    sample_rows = []
    for r in rows[:PREVIEW_LIMIT]:
        content = build_content(dict(r))
        sample_rows.append({
            "mapc": r['mapc'],
            "dieu_ten": r['dieu_ten'],
            "chu_de_id": str(r['chu_de_id']),
            "chu_de": r['chu_de'],
            "de_muc": r['de_muc'],
            "chuong_ten": r.get('chuong_ten') or '',
            "vbqppl": r.get('vbqppl') or '',
            "content_len": len(content),
            "content_preview": content[:600],
        })

    preview = {
        "stats": {
            "total_vectors": total,
            "theo_chu_de": chude_stats,
            "content_length": {
                "min": min(content_lens) if content_lens else 0,
                "max": max(content_lens) if content_lens else 0,
                "avg": round(sum(content_lens) / len(content_lens), 1) if content_lens else 0,
            },
        },
        "sample_rows": sample_rows,
    }

    log(f"  Tổng vectors (pddieu) : {total}")
    log(f"  Theo chủ đề:")
    for cd, cnt in sorted(chude_stats.items(), key=lambda x: -x[1])[:10]:
        log(f"    {cd}: {cnt} điều")
    if len(chude_stats) > 10:
        log(f"    ... và {len(chude_stats) - 10} chủ đề khác")
    log(
        f"  Độ dài content        : "
        f"min={preview['stats']['content_length']['min']} | "
        f"max={preview['stats']['content_length']['max']} | "
        f"avg={preview['stats']['content_length']['avg']}"
    )
    return preview, rows


def save_preview(preview: dict):
    with open(PREVIEW_PATH, "w", encoding="utf-8") as f:
        json.dump(preview, f, ensure_ascii=False, indent=2, default=str)
    log(f"Preview JSON đã lưu: {PREVIEW_PATH}")


def export_rows_to_json(rows: list, path: str = None):
    """Export toàn bộ rows (đã build content + metadata) ra JSON để embed trên Colab."""
    out_path = path or EXPORT_PATH
    data = []
    for r in rows:
        content = build_content(dict(r))
        if not content.strip():
            continue
        data.append({
            "id": f"pddieu_{r['mapc']}",
            "content": content,
            "metadata": {
                "dieu_mapc":   str(r['mapc']),
                "dieu_ten":    str(r['dieu_ten'] or ''),
                "chu_de_id":   str(r['chu_de_id']),
                "chu_de":      str(r['chu_de'] or ''),
                "de_muc":      str(r['de_muc'] or ''),
                "chuong_ten":  str(r.get('chuong_ten') or ''),
            },
        })
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    log(f"Đã export {len(data)} rows → {out_path} ({os.path.getsize(out_path) / 1024 / 1024:.1f} MB)")
    log("Tiếp theo: upload file này lên Google Colab để embed với GPU.")


# ── Ingest ─────────────────────────────────────────────────────────────────────

def ingest(rows: list):
    from app.rag.retrieval import get_rag_system

    log("Khởi tạo RAG system (tải embedding model)...")
    t0 = time.time()
    rag = get_rag_system()
    log(f"Embedding model sẵn sàng sau {time.time() - t0:.1f}s")

    total = len(rows)
    total_ingested = 0
    t_start = time.time()

    log(f"Bắt đầu embed theo batch {BATCH_SIZE} rows (tổng: {total})...")

    for batch_start in range(0, total, BATCH_SIZE):
        batch = rows[batch_start: batch_start + BATCH_SIZE]
        t_batch = time.time()

        rows_to_add = []
        for r in batch:
            content = build_content(dict(r))
            if not content.strip():
                continue
            rows_to_add.append({
                "id": f"pddieu_{r['mapc']}",
                "content": content,
                "metadata": {
                    "dieu_mapc":   str(r['mapc']),
                    "dieu_ten":    str(r['dieu_ten'] or ''),
                    "chu_de_id":   str(r['chu_de_id']),
                    "chu_de":      str(r['chu_de'] or ''),
                    "de_muc":      str(r['de_muc'] or ''),
                    "chuong_ten":  str(r.get('chuong_ten') or ''),
                },
            })

        batch_idx = batch_start // BATCH_SIZE + 1
        log(f"  Batch {batch_idx}: embed {len(rows_to_add)} rows...")
        rag.add_documents_direct(rows_to_add)
        total_ingested += len(rows_to_add)

        elapsed = time.time() - t_start
        batch_time = time.time() - t_batch
        pct = total_ingested / total * 100
        speed = total_ingested / elapsed if elapsed > 0 else 0
        eta = (total - total_ingested) / speed if speed > 0 else 0
        log(
            f"  → [{total_ingested}/{total}] {pct:.1f}% | "
            f"batch={batch_time:.1f}s | {speed:.0f} rows/s | ETA={eta:.0f}s"
        )

    log(f"Hoàn tất: {total_ingested} vectors sau {time.time() - t_start:.1f}s")
    return total_ingested


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    do_reset = "--reset" in sys.argv
    preview_only = "--preview-only" in sys.argv
    export_json = "--export-json" in sys.argv

    # Parse --chude-id <value>
    chude_id = None
    for i, arg in enumerate(sys.argv):
        if arg == "--chude-id" and i + 1 < len(sys.argv):
            chude_id = sys.argv[i + 1]
            break

    print("=" * 60)
    log("PDDIEU → ChromaDB Ingest Tool")
    if chude_id:
        log(f"Chế độ: chỉ ingest chủ đề ID = {chude_id}")
    print("=" * 60)

    if do_reset and not preview_only:
        log("Reset ChromaDB...")
        reset_chroma()

    log("Kết nối MySQL...")
    with get_db() as conn:
        log("Kết nối thành công.")

        # Bước 1: preview
        log("─" * 40)
        log("BƯỚC 1: Tải dữ liệu và tạo preview")
        log("─" * 40)
        preview, rows = build_preview(conn, chude_id)
        save_preview(preview)

        if preview_only:
            log("Chế độ --preview-only: dừng tại đây.")
            return

        if export_json:
            log("─" * 40)
            log("BƯỚC 2: Export JSON (để embed trên Colab)")
            log("─" * 40)
            export_rows_to_json(rows)
            return

        # Bước 2: embed
        print()
        log("─" * 40)
        log("BƯỚC 2: Embedding và lưu vào ChromaDB")
        log("─" * 40)
        ans = input("Tiến hành embedding? (y/n): ").strip().lower()
        if ans != "y":
            log("Hủy. File preview đã được lưu để tham khảo.")
            return

        total = ingest(rows)

    print("=" * 60)
    log(f"DONE — {total} vectors đã được index vào ChromaDB.")
    print("=" * 60)


if __name__ == "__main__":
    main()
