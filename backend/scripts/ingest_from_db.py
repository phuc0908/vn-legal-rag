"""
Ingest bảng vb_chimuc từ MySQL vào ChromaDB.
Mỗi row trong vb_chimuc = 1 vector (không split thêm).

Metadata mỗi vector:
  - id_vb          : ID văn bản (FK → vbpl.id)
  - ten_vb         : Tên đầy đủ văn bản (trích từ HTML)
  - so_hieu        : Số hiệu (vd: 09/2021/TT-BCA)
  - co_quan        : Cơ quan ban hành (vd: BỘ CÔNG AN)
  - loai_vb        : Loại văn bản (THÔNG TƯ, LUẬT, NGHỊ ĐỊNH...)
  - ten_chuong_cha : Tiêu đề chương cha (nếu là điều)
  - tieu_de        : Dòng đầu tiên của noi_dung

Usage:
    python scripts/ingest_from_db.py                  # ingest toàn bộ
    python scripts/ingest_from_db.py --reset          # xóa ChromaDB cũ rồi ingest
    python scripts/ingest_from_db.py --preview-only   # chỉ tạo file JSON preview, không embed
"""

import sys
import os
import re
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import get_db

BATCH_SIZE = 500
PREVIEW_LIMIT = 50  # Số rows tối đa trong tat_ca_rows của file preview
PREVIEW_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vb_chimuc_preview.json")


# ── Helpers ────────────────────────────────────────────────────────────────────

def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def reset_chroma():
    import shutil
    chroma_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma_db")
    if os.path.exists(chroma_path):
        shutil.rmtree(chroma_path)
        log(f"Đã xóa ChromaDB: {chroma_path}")
    else:
        log("ChromaDB chưa tồn tại, bỏ qua bước reset.")


def _strip_html(html: str) -> str:
    """Xóa toàn bộ thẻ HTML, chuẩn hóa khoảng trắng."""
    text = re.sub(r'<[^>]+>', ' ', html or '')
    return re.sub(r'\s+', ' ', text).strip()


def _extract_vb_info(html: str) -> dict:
    """
    Trích thông tin văn bản từ HTML của vbpl.noidung.
    Trả về: {co_quan, so_hieu, loai_vb, ten_vb}
    """
    text = _strip_html(html)

    # Cơ quan ban hành — thường là dòng đầu tiên viết hoa
    co_quan = ""
    m = re.search(
        r'\b(BỘ|CHÍNH PHỦ|QUỐC HỘI|ỦY BAN|HỘI ĐỒNG|TỔNG CỤC|CỤC|SỞ|UBND|BAN)[^\n]{0,80}',
        text[:500],
    )
    if m:
        co_quan = m.group(0).strip()[:100]

    # Số hiệu văn bản
    so_hieu = ""
    m = re.search(r'Số[:\s]*([0-9A-ZĐ/\-\.]+(?:/[0-9A-ZĐ\-\.]+)+)', text[:500])
    if m:
        so_hieu = m.group(1).strip()

    # Loại văn bản
    loai_vb = ""
    for loai in ['LUẬT', 'BỘ LUẬT', 'PHÁP LỆNH', 'NGHỊ QUYẾT', 'NGHỊ ĐỊNH',
                 'THÔNG TƯ LIÊN TỊCH', 'THÔNG TƯ', 'QUYẾT ĐỊNH', 'CHỈ THỊ',
                 'HIẾN PHÁP', 'LỆNH']:
        if loai in text[:1000]:
            loai_vb = loai
            break

    # Tên văn bản — câu sau loại văn bản, thường là mô tả nội dung
    ten_vb = ""
    if loai_vb:
        pattern = rf'{re.escape(loai_vb)}\s+(.{{10,300}}?)(?:\s+Căn cứ|\s+Điều\s+1|\s+$)'
        m = re.search(pattern, text[:2000])
        if m:
            ten_vb = re.sub(r'\s+', ' ', m.group(1)).strip()[:300]

    return {
        "co_quan": co_quan,
        "so_hieu": so_hieu,
        "loai_vb": loai_vb,
        "ten_vb": ten_vb,
    }


def _extract_title(noi_dung: str) -> str:
    """Lấy dòng đầu tiên có nghĩa từ noi_dung."""
    for line in (noi_dung or "").strip().splitlines():
        line = line.strip()
        if line:
            return line[:200]
    return ""


# ── Load toàn bộ metadata văn bản (1 lần, ~1817 records) ─────────────────────

def load_vb_info_map(conn) -> dict:
    """
    Trả về dict: {id_vb: {co_quan, so_hieu, loai_vb, ten_vb, chu_de, de_muc}}
    - Trích HTML từ vbpl để lấy co_quan, so_hieu, loai_vb, ten_vb
    - Join với pddieu → pdchude/pddemuc để lấy chủ đề và đề mục
    """
    # 1. Trích thông tin từ HTML
    log("Đang đọc và phân tích metadata từ bảng vbpl (~1817 văn bản)...")
    t0 = time.time()
    with conn.cursor() as cur:
        cur.execute("SELECT id, LEFT(noidung, 3000) as html_head FROM vbpl WHERE noidung IS NOT NULL")
        rows = cur.fetchall()

    vb_map = {}
    for r in rows:
        vb_map[str(r['id'])] = _extract_vb_info(r['html_head'] or '')
    log(f"  Phân tích HTML xong {len(vb_map)} văn bản sau {time.time()-t0:.1f}s")

    # 2. Lấy chủ đề + đề mục từ pháp điển (join qua ItemID trong vbqppl_link)
    log("Đang map chủ đề và đề mục từ pháp điển...")
    with conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT
                SUBSTRING_INDEX(SUBSTRING_INDEX(d.vbqppl_link, 'ItemID=', -1), '#', 1) AS item_id,
                cd.ten AS chu_de,
                dm.ten AS de_muc
            FROM pddieu d
            JOIN pdchude cd ON d.chude_id = cd.id
            JOIN pddemuc dm  ON d.demuc_id = dm.id
            WHERE d.vbqppl_link IS NOT NULL
        """)
        topic_rows = cur.fetchall()

    # Một văn bản có thể thuộc nhiều đề mục — gom tất cả lại
    topic_map = {}
    for r in topic_rows:
        iid = str(r['item_id']).strip()
        if not iid:
            continue
        if iid not in topic_map:
            topic_map[iid] = {"chu_de": set(), "de_muc": set()}
        topic_map[iid]["chu_de"].add(r['chu_de'])
        topic_map[iid]["de_muc"].add(r['de_muc'])

    # Merge vào vb_map
    matched = 0
    for iid, topics in topic_map.items():
        if iid in vb_map:
            vb_map[iid]["chu_de"] = ", ".join(sorted(topics["chu_de"]))
            vb_map[iid]["de_muc"] = ", ".join(sorted(topics["de_muc"]))
            matched += 1

    log(f"  Map chủ đề/đề mục: {matched}/{len(vb_map)} văn bản có thông tin pháp điển")
    return vb_map


# ── Load toàn bộ bảng vb_chimuc vào dict để tra cứu chương cha ───────────────

def load_chimuc_map(conn) -> dict:
    """
    Trả về dict: {id: noi_dung_dong_dau} để tra cứu tên chương cha.
    Chỉ load các row là chương (chi_muc_cha IS NULL).
    """
    log("Đang đọc danh sách chương cha từ vb_chimuc...")
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, LEFT(noi_dung, 300) as nd FROM vb_chimuc WHERE chi_muc_cha IS NULL"
        )
        rows = cur.fetchall()
    result = {}
    for r in rows:
        result[int(r['id'])] = _extract_title(r['nd'] or '')
    log(f"  Đã load {len(result)} chương cha")
    return result


# ── Preview ────────────────────────────────────────────────────────────────────

def build_preview(conn, vb_map: dict, chimuc_map: dict) -> dict:
    log("Đang tạo preview dữ liệu...")
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) as total FROM vb_chimuc")
        total = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) as cnt FROM vb_chimuc WHERE noi_dung IS NULL OR noi_dung = ''")
        empty = cur.fetchone()["cnt"]

        cur.execute("SELECT COUNT(*) as cnt FROM vb_chimuc WHERE chi_muc_cha IS NULL")
        chuong_count = cur.fetchone()["cnt"]

        cur.execute(
            "SELECT MIN(CHAR_LENGTH(noi_dung)) as min_len, "
            "MAX(CHAR_LENGTH(noi_dung)) as max_len, "
            "AVG(CHAR_LENGTH(noi_dung)) as avg_len "
            "FROM vb_chimuc WHERE noi_dung IS NOT NULL AND noi_dung != ''"
        )
        length_stats = cur.fetchone()

        # Lấy một số rows mẫu (giới hạn PREVIEW_LIMIT để file không quá nặng)
        cur.execute("""
            SELECT
                id, id_vb, chi_muc_cha,
                CHAR_LENGTH(noi_dung) as noi_dung_len,
                LEFT(noi_dung, 2000) as noi_dung_preview
            FROM vb_chimuc
            WHERE noi_dung IS NOT NULL AND noi_dung != ''
            ORDER BY id_vb, id
            LIMIT %s
        """, (PREVIEW_LIMIT,))
        all_rows_raw = cur.fetchall()

    # Làm giàu rows mẫu với metadata đầy đủ
    all_rows = []
    for r in all_rows_raw:
        id_vb = str(r['id_vb'])
        info = vb_map.get(id_vb, {})
        cha_id = int(r['chi_muc_cha']) if r['chi_muc_cha'] is not None else None
        ten_chuong_cha = chimuc_map.get(cha_id, "") if cha_id else ""
        all_rows.append({
            "id": r["id"],
            "id_vb": id_vb,
            "chu_de": info.get("chu_de", ""),
            "de_muc": info.get("de_muc", ""),
            "ten_chuong_cha": ten_chuong_cha,
            "loai_vb": info.get("loai_vb", ""),
            "so_hieu": info.get("so_hieu", ""),
            "ten_vb": info.get("ten_vb", ""),
            "co_quan": info.get("co_quan", ""),
            "la_chuong": r["chi_muc_cha"] is None,
            "noi_dung_len": r["noi_dung_len"],
            "noi_dung": r["noi_dung_preview"],
        })

    preview = {
        "stats": {
            "total_rows": total,
            "rows_with_content": total - empty,
            "rows_empty": empty,
            "unique_van_ban": len(set(r["id_vb"] for r in all_rows_raw)),
            "rows_la_chuong": chuong_count,
            "rows_la_dieu": total - chuong_count,
            "noi_dung_length": {
                "min": length_stats["min_len"],
                "max": length_stats["max_len"],
                "avg": round(length_stats["avg_len"] or 0, 1),
            },
        },
        "tat_ca_rows": all_rows,  # giới hạn PREVIEW_LIMIT rows mẫu
    }

    log(f"  Tổng rows         : {total}")
    log(f"  Có nội dung       : {total - empty}")
    log(f"  Là chương (gốc)   : {chuong_count}")
    log(f"  Là điều (con)     : {total - chuong_count}")
    log(f"  Số văn bản (id_vb): {preview['stats']['unique_van_ban']}")
    log(f"  Độ dài noi_dung   : min={length_stats['min_len']} | max={length_stats['max_len']} | avg={round(length_stats['avg_len'] or 0, 1)}")
    return preview


def save_preview(preview: dict):
    with open(PREVIEW_PATH, "w", encoding="utf-8") as f:
        json.dump(preview, f, ensure_ascii=False, indent=2, default=str)
    log(f"Preview JSON đã lưu: {PREVIEW_PATH}")


# ── Ingest ─────────────────────────────────────────────────────────────────────

def fetch_batches(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) as cnt FROM vb_chimuc WHERE noi_dung IS NOT NULL AND noi_dung != ''")
        total = cur.fetchone()["cnt"]

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


def ingest(conn, vb_map: dict, chimuc_map: dict):
    from app.rag.retrieval import get_rag_system

    log("Khởi tạo RAG system (tải embedding model)...")
    t0 = time.time()
    rag = get_rag_system()
    log(f"Embedding model sẵn sàng sau {time.time() - t0:.1f}s")

    total_ingested = 0
    t_start = time.time()

    log(f"Bắt đầu embed theo batch {BATCH_SIZE} rows...")
    for batch_idx, (batch, total) in enumerate(fetch_batches(conn), 1):
        t_batch = time.time()

        rows_to_add = []
        for row in batch:
            id_vb = str(row['id_vb'])
            cha_id = int(row['chi_muc_cha']) if row['chi_muc_cha'] is not None else None
            vb_info = vb_map.get(id_vb, {})

            rows_to_add.append({
                "id": f"vb_chimuc_{row['id']}",
                "content": row["noi_dung"],
                "metadata": {
                    "id_vb": id_vb,
                    "tieu_de": _extract_title(row["noi_dung"]),
                    "ten_chuong_cha": chimuc_map.get(cha_id, "") if cha_id else "",
                    "co_quan": vb_info.get("co_quan", ""),
                    "so_hieu": vb_info.get("so_hieu", ""),
                    "loai_vb": vb_info.get("loai_vb", ""),
                    "ten_vb": vb_info.get("ten_vb", ""),
                    "chu_de": vb_info.get("chu_de", ""),
                    "de_muc": vb_info.get("de_muc", ""),
                },
            })

        log(f"  Batch {batch_idx}: embed {len(rows_to_add)} rows (đã xử lý: {total_ingested})...")
        rag.add_documents_direct(rows_to_add)
        total_ingested += len(rows_to_add)

        elapsed = time.time() - t_start
        batch_time = time.time() - t_batch
        pct = total_ingested / total * 100
        speed = total_ingested / elapsed if elapsed > 0 else 0
        eta = (total - total_ingested) / speed if speed > 0 else 0
        log(f"  → [{total_ingested}/{total}] {pct:.1f}% | batch={batch_time:.1f}s | {speed:.0f} rows/s | ETA={eta:.0f}s")

    log(f"Hoàn tất: {total_ingested} vectors sau {time.time() - t_start:.1f}s")
    return total_ingested


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    do_reset = "--reset" in sys.argv
    preview_only = "--preview-only" in sys.argv

    print("=" * 60)
    log("VB_CHIMUC → ChromaDB Ingest Tool")
    print("=" * 60)

    if do_reset and not preview_only:
        log("Reset ChromaDB...")
        reset_chroma()

    log("Kết nối MySQL...")
    with get_db() as conn:
        log("Kết nối thành công.")

        # Bước 1: load metadata văn bản và chương cha
        log("─" * 40)
        log("BƯỚC 1: Load metadata từ DB")
        log("─" * 40)
        vb_map = load_vb_info_map(conn)
        chimuc_map = load_chimuc_map(conn)

        # Bước 2: tạo preview JSON
        log("─" * 40)
        log("BƯỚC 2: Tạo preview dữ liệu")
        log("─" * 40)
        preview = build_preview(conn, vb_map, chimuc_map)
        save_preview(preview)

        if preview_only:
            log("Chế độ --preview-only: dừng tại đây.")
            return

        # Bước 3: embed
        print()
        log("─" * 40)
        log("BƯỚC 3: Embedding và lưu vào ChromaDB")
        log("─" * 40)
        ans = input("Tiến hành embedding? (y/n): ").strip().lower()
        if ans != "y":
            log("Hủy. File preview đã được lưu để tham khảo.")
            return

        total = ingest(conn, vb_map, chimuc_map)

    print("=" * 60)
    log(f"DONE — {total} vectors đã được index vào ChromaDB.")
    print("=" * 60)


if __name__ == "__main__":
    main()
