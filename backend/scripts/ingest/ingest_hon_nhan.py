"""
Ingest corpus rieng cho module Hon nhan & Gia dinh.

Nguon mac dinh:
  1. De muc "Hon nhan va gia dinh" trong Phap dien.
  2. Chuong XVII BLHS ve cac toi xam pham che do hon nhan va gia dinh.
  3. Cac dieu lien quan truc tiep qua bang pdmuclienquan.
  4. Cac dieu khac trong DB match keyword hon nhan/gia dinh.

Dung --core-only neu muon quay ve corpus cu chi gom 2 nguon loi.

Usage:
    python scripts/ingest/ingest_hon_nhan.py
    python scripts/ingest/ingest_hon_nhan.py --preview
    python scripts/ingest/ingest_hon_nhan.py --export-json
    python scripts/ingest/ingest_hon_nhan.py --bm25-only
    python scripts/ingest/ingest_hon_nhan.py --reset
    python scripts/ingest/ingest_hon_nhan.py --core-only
"""

import json
import os
import re
import sys
import time
from collections import Counter

# --- path setup ---
_SCRIPT = os.path.abspath(__file__)
_SCRIPTS_DIR = os.path.dirname(_SCRIPT)
BASE_DIR = os.path.dirname(os.path.dirname(_SCRIPTS_DIR))
sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)
# ---

from app.db.database import get_db


DEMUC_HNGD_ID = "4913a1cf-5f78-471c-a807-ed5f8c57aaee"
CHUONG_XVII_HS_MAPC = "1600100000000000200001700000000000000000"

CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db_hon_nhan")
BM25_PATH = os.path.join(BASE_DIR, "bm25_hon_nhan.pkl")
EXPORT_PATH = os.path.join(_SCRIPTS_DIR, "hon_nhan_export.json")

BATCH_SIZE = 100

# Vietnamese keyword variants are kept here so MySQL can match the real DB text.
HON_NHAN_KEYWORDS_VI = [
    "hôn nhân",
    "gia đình",
    "kết hôn",
    "ly hôn",
    "vợ",
    "chồng",
    "con chung",
    "con riêng",
    "cấp dưỡng",
    "nuôi con",
    "quyền nuôi con",
    "tài sản chung",
    "tài sản riêng",
    "chế độ tài sản",
    "cha mẹ",
    "xác định cha",
    "xác định mẹ",
    "nhận cha",
    "nhận mẹ",
    "mang thai hộ",
    "bạo lực gia đình",
    "chung sống như vợ chồng",
    "ngoại tình",
    "tảo hôn",
    "cưỡng ép kết hôn",
    "cản trở kết hôn",
    "một vợ một chồng",
]

LAW_TYPE_PREFIXES = [
    "Bộ luật",
    "Luật",
    "Nghị định",
    "Thông tư",
    "Nghị quyết",
    "Quyết định",
    "Pháp lệnh",
]


def log(msg: str):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", text).strip()


def split_khoans(noidung: str) -> list[str]:
    positions = [m.start() for m in re.finditer(r"(?<![0-9])(\d+)\. ", noidung)]
    if len(positions) < 2:
        return [noidung]

    parts = []
    for i, pos in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(noidung)
        parts.append(noidung[pos:end].strip())
    return parts


def normalize_for_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("_")


def parse_vbqppl(vbqppl: str) -> dict:
    text = str(vbqppl or "").strip()
    loai_vb = ""
    so_hieu = ""

    for prefix in LAW_TYPE_PREFIXES:
        if text.lower().startswith(prefix.lower()):
            loai_vb = prefix
            break

    match = re.search(r"\b\d{1,4}/[A-Z0-9./-]+", text, flags=re.IGNORECASE)
    if match:
        so_hieu = match.group(0)

    return {
        "loai_vb": loai_vb,
        "so_hieu": so_hieu,
        "ten_vb": text,
    }


def build_header(row: dict) -> str:
    parts = []
    if row.get("chu_de"):
        parts.append(f"Chủ đề: {row['chu_de']}")
    if row.get("de_muc"):
        parts.append(f"Đề mục: {row['de_muc']}")
    if row.get("chuong_ten"):
        parts.append(f"Chương: {row['chuong_ten']}")
    if row.get("source_kind") and row.get("source_kind") != "core":
        parts.append(f"Nguồn mở rộng: {row['source_kind']}")
    return " | ".join(parts)


def build_metadata(row: dict) -> dict:
    vb_meta = parse_vbqppl(row.get("vbqppl") or "")
    dieu_ten = str(row.get("dieu_ten") or "")
    return {
        "dieu_mapc": str(row["mapc"]),
        "dieu_ten": dieu_ten,
        "dieu_so": str(row.get("dieu_so") or ""),
        "chu_de_id": str(row.get("chu_de_id") or ""),
        "chu_de": str(row.get("chu_de") or ""),
        "de_muc": str(row.get("de_muc") or ""),
        "chuong_ten": str(row.get("chuong_ten") or ""),
        "tieu_de": dieu_ten,
        "loai_vb": vb_meta["loai_vb"],
        "so_hieu": vb_meta["so_hieu"],
        "ten_vb": vb_meta["ten_vb"],
        "url": str(row.get("vbqppl_link") or ""),
        "source_kind": str(row.get("source_kind") or "core"),
        "source_reason": str(row.get("source_reason") or ""),
        "module": "hon_nhan",
    }


def make_chunks(row: dict) -> list[dict]:
    noidung = strip_html(row.get("noidung", ""))
    header = build_header(row)
    dieu_ten = str(row.get("dieu_ten") or "")
    vbqppl = str(row.get("vbqppl") or "")
    metadata = build_metadata(row)
    khoans = split_khoans(noidung)
    base_id = f"pddieu_{normalize_for_id(row['mapc'])}"

    def make_content(khoan_text: str) -> str:
        parts = [p for p in [header, dieu_ten, khoan_text] if p]
        if vbqppl:
            parts.append(f"Văn bản: {vbqppl}")
        return "\n".join(parts)

    if len(khoans) == 1:
        content = make_content(noidung)
        if not content.strip():
            return []
        return [{"id": base_id, "content": content, "metadata": metadata}]

    chunks = []
    for i, khoan_text in enumerate(khoans, 1):
        content = make_content(khoan_text)
        if content.strip():
            chunks.append({
                "id": f"{base_id}_k{i}",
                "content": content,
                "metadata": {**metadata, "khoan_index": i},
            })
    return chunks


CORE_SQL = """
    SELECT
        d.mapc,
        d.ten AS dieu_ten,
        d.chimuc AS dieu_so,
        d.noidung,
        d.vbqppl,
        d.vbqppl_link,
        cd.id AS chu_de_id,
        cd.ten AS chu_de,
        dm.ten AS de_muc,
        c.ten AS chuong_ten,
        c.chimuc AS chuong_so,
        'core' AS source_kind,
        CASE
            WHEN d.demuc_id = %s THEN 'demuc_hon_nhan_gia_dinh'
            WHEN d.chuong_id = %s THEN 'chuong_xvii_hinh_su'
            ELSE 'core'
        END AS source_reason
    FROM pddieu d
    JOIN pdchude cd ON d.chude_id = cd.id
    JOIN pddemuc dm ON d.demuc_id = dm.id
    LEFT JOIN pdchuong c ON d.chuong_id = c.mapc
    WHERE
        d.noidung IS NOT NULL AND d.noidung != ''
        AND (d.muc_id IS NULL OR d.muc_id != d.mapc)
        AND (d.demuc_id = %s OR d.chuong_id = %s)
    ORDER BY cd.stt, dm.stt, c.stt, d.stt
"""

RELATED_SQL = """
    SELECT
        d.mapc,
        d.ten AS dieu_ten,
        d.chimuc AS dieu_so,
        d.noidung,
        d.vbqppl,
        d.vbqppl_link,
        cd.id AS chu_de_id,
        cd.ten AS chu_de,
        dm.ten AS de_muc,
        c.ten AS chuong_ten,
        c.chimuc AS chuong_so,
        'related' AS source_kind,
        'pdmuclienquan_to_core' AS source_reason
    FROM pddieu d
    JOIN pdchude cd ON d.chude_id = cd.id
    JOIN pddemuc dm ON d.demuc_id = dm.id
    LEFT JOIN pdchuong c ON d.chuong_id = c.mapc
    WHERE
        d.noidung IS NOT NULL AND d.noidung != ''
        AND (d.muc_id IS NULL OR d.muc_id != d.mapc)
        AND EXISTS (
            SELECT 1
            FROM pdmuclienquan r
            JOIN pddieu seed
              ON seed.mapc = CASE
                    WHEN r.dieu_id1_id = d.mapc THEN r.dieu_id2_id
                    ELSE r.dieu_id1_id
                 END
            WHERE
                (r.dieu_id1_id = d.mapc OR r.dieu_id2_id = d.mapc)
                AND (seed.demuc_id = %s OR seed.chuong_id = %s)
        )
    ORDER BY cd.stt, dm.stt, c.stt, d.stt
"""


def keyword_sql() -> tuple[str, list[str]]:
    fields = "LOWER(CONCAT_WS(' ', d.ten, d.noidung, d.vbqppl))"
    predicates = []
    params = []
    for keyword in HON_NHAN_KEYWORDS_VI:
        predicates.append(f"{fields} LIKE %s")
        params.append(f"%{keyword.lower()}%")

    sql = f"""
        SELECT
            d.mapc,
            d.ten AS dieu_ten,
            d.chimuc AS dieu_so,
            d.noidung,
            d.vbqppl,
            d.vbqppl_link,
            cd.id AS chu_de_id,
            cd.ten AS chu_de,
            dm.ten AS de_muc,
            c.ten AS chuong_ten,
            c.chimuc AS chuong_so,
            'keyword' AS source_kind,
            'keyword_match' AS source_reason
        FROM pddieu d
        JOIN pdchude cd ON d.chude_id = cd.id
        JOIN pddemuc dm ON d.demuc_id = dm.id
        LEFT JOIN pdchuong c ON d.chuong_id = c.mapc
        WHERE
            d.noidung IS NOT NULL AND d.noidung != ''
            AND (d.muc_id IS NULL OR d.muc_id != d.mapc)
            AND ({' OR '.join(predicates)})
        ORDER BY cd.stt, dm.stt, c.stt, d.stt
    """
    return sql, params


def fetch_with_label(conn, sql: str, params: tuple | list, label: str) -> list[dict]:
    log(f"Đang tải nguồn {label}...")
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    log(f"  {label}: {len(rows)} điều")
    return [dict(r) for r in rows]


def merge_rows(groups: list[list[dict]]) -> list[dict]:
    priority = {"core": 0, "related": 1, "keyword": 2}
    merged = {}
    for rows in groups:
        for row in rows:
            mapc = str(row["mapc"])
            current = merged.get(mapc)
            if current is None:
                merged[mapc] = row
                continue
            if priority.get(row.get("source_kind"), 99) < priority.get(current.get("source_kind"), 99):
                merged[mapc] = row

    return sorted(
        merged.values(),
        key=lambda r: (
            priority.get(r.get("source_kind"), 99),
            str(r.get("chu_de") or ""),
            str(r.get("de_muc") or ""),
            str(r.get("chuong_ten") or ""),
            str(r.get("dieu_so") or ""),
            str(r.get("mapc") or ""),
        ),
    )


def fetch_rows(conn, include_related: bool = True, include_keyword: bool = True) -> list[dict]:
    groups = [
        fetch_with_label(
            conn,
            CORE_SQL,
            (DEMUC_HNGD_ID, CHUONG_XVII_HS_MAPC, DEMUC_HNGD_ID, CHUONG_XVII_HS_MAPC),
            "core",
        )
    ]

    if include_related:
        groups.append(
            fetch_with_label(
                conn,
                RELATED_SQL,
                (DEMUC_HNGD_ID, CHUONG_XVII_HS_MAPC),
                "related",
            )
        )

    if include_keyword:
        sql, params = keyword_sql()
        groups.append(fetch_with_label(conn, sql, params, "keyword"))

    rows = merge_rows(groups)

    by_kind = Counter(r.get("source_kind") or "unknown" for r in rows)
    by_demuc = Counter(r.get("de_muc") or "(empty)" for r in rows)
    log(f"Tổng sau dedupe: {len(rows)} điều")
    for kind, count in by_kind.items():
        log(f"  source_kind={kind}: {count} điều")
    log("Top đề mục:")
    for name, count in by_demuc.most_common(12):
        log(f"  - {name}: {count} điều")
    return rows


def build_all_chunks(rows: list[dict]) -> list[dict]:
    chunks = []
    for row in rows:
        chunks.extend(make_chunks(dict(row)))

    by_kind = Counter(c["metadata"].get("source_kind") for c in chunks)
    log(f"{len(rows)} điều -> {len(chunks)} chunks")
    for kind, count in by_kind.items():
        log(f"  chunks source_kind={kind}: {count}")
    return chunks


def preview(chunks: list[dict], n: int = 10):
    print("=" * 70)
    print(f"PREVIEW - {n} chunk đầu (tổng {len(chunks)} chunks)")
    print("=" * 70)
    for i, chunk in enumerate(chunks[:n], 1):
        meta = chunk["metadata"]
        print(f"\n-- Chunk {i} -- id: {chunk['id']}")
        print(f"source_kind={meta.get('source_kind')} | dieu={meta.get('dieu_ten')}")
        print(chunk["content"][:600])
        if len(chunk["content"]) > 600:
            print("...")
    print("=" * 70)


def export_json(chunks: list[dict]):
    with open(EXPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False)
    size_mb = os.path.getsize(EXPORT_PATH) / 1024 / 1024
    log(f"Exported {len(chunks)} chunks -> {EXPORT_PATH} ({size_mb:.2f} MB)")


def ingest(chunks: list[dict]):
    from app.core.config import settings
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import Chroma

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
            f"[{done}/{total}] {done / total * 100:.1f}% | "
            f"batch={time.time() - t_batch:.1f}s | ETA={eta:.0f}s"
        )

    log(f"Hoàn tất embed: {total} chunks sau {time.time() - t_start:.1f}s")


def build_bm25(chunks: list[dict]):
    from app.rag.retrieval import BM25Index

    log(f"Đang build BM25 index ({len(chunks)} chunks)...")
    bm25 = BM25Index(index_path=BM25_PATH)
    bm25.build(chunks)
    bm25.save()
    log(f"BM25 index đã lưu: {BM25_PATH}")


def reset_chroma():
    import shutil

    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)
        log(f"Đã xóa: {CHROMA_PATH}")
    else:
        log("chroma_db_hon_nhan/ chưa tồn tại, bỏ qua.")


def main():
    do_reset = "--reset" in sys.argv
    do_preview = "--preview" in sys.argv
    do_export = "--export-json" in sys.argv
    do_bm25 = "--bm25-only" in sys.argv
    core_only = "--core-only" in sys.argv
    no_keyword = "--no-keyword" in sys.argv
    no_related = "--no-related" in sys.argv

    include_related = not core_only and not no_related
    include_keyword = not core_only and not no_keyword

    print("=" * 60)
    log("Ingest Module: Hôn nhân & Gia đình")
    log(f"  ChromaDB path : {CHROMA_PATH}")
    log(f"  BM25 path     : {BM25_PATH}")
    log(f"  related       : {include_related}")
    log(f"  keyword       : {include_keyword}")
    print("=" * 60)

    if do_reset:
        reset_chroma()

    log("Kết nối MySQL...")
    with get_db() as conn:
        rows = fetch_rows(
            conn,
            include_related=include_related,
            include_keyword=include_keyword,
        )

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

    ans = input("Tiến hành embed vào chroma_db_hon_nhan/? (y/n): ").strip().lower()
    if ans != "y":
        log("Hủy.")
        return

    ingest(chunks)

    ans2 = input("Build BM25 index (bm25_hon_nhan.pkl)? (y/n): ").strip().lower()
    if ans2 == "y":
        build_bm25(chunks)

    print("=" * 60)
    log("DONE - module hon_nhan sẵn sàng.")
    print("=" * 60)


if __name__ == "__main__":
    main()
