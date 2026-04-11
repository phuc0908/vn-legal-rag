"""
Migration: Tạo bảng pdmuc và thêm cột muc_id vào pddieu.

Cấu trúc mapc:
  pddieu.mapc = chuong_id(20 chars) + muc_encoded(6 chars) + ...
  Ví dụ: 0100800000000000600000010000000000000000
            chuong(20)=01008000000000006000
            muc(6)=000100  → Mục 1 trong chương này

Muc header row: mapc kết thúc bằng 14 số 0, muc_encoded != 000000
Dieu thường:    mapc không kết thúc 14 số 0

Chạy:
    python scripts/migrate_pdmuc.py           # dry run (chỉ in thống kê)
    python scripts/migrate_pdmuc.py --apply   # thực hiện migration
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import get_db


def muc_encoded_to_so(muc_encoded: str) -> int:
    """'000100' → 1, '000200' → 2, '001000' → 10"""
    try:
        return int(muc_encoded) // 100
    except ValueError:
        return 0


def run(apply: bool):
    with get_db() as conn:
        with conn.cursor() as cur:

            # ── 1. Tạo bảng pdmuc ─────────────────────────────────────────
            print("[1] Tạo bảng pdmuc (nếu chưa có)...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS pdmuc (
                    mapc        VARCHAR(40)  NOT NULL PRIMARY KEY,
                    chuong_id   VARCHAR(40)  NOT NULL,
                    chimuc      INT          NOT NULL,
                    ten         VARCHAR(50)  NOT NULL,
                    stt         INT          NOT NULL DEFAULT 0,
                    INDEX idx_chuong (chuong_id)
                ) CHARACTER SET utf8mb4
            """)
            if apply:
                conn.commit()
                print("   → Bảng pdmuc đã tạo/tồn tại.")

            # ── 2. Lấy tất cả Mục rows từ pddieu ──────────────────────────
            print("[2] Đọc Mục rows từ pddieu...")
            cur.execute("""
                SELECT mapc, ten, stt, chuong_id, chimuc
                FROM pddieu
                WHERE RIGHT(mapc, 14) = '00000000000000'
                  AND SUBSTRING(mapc, 21, 6) != '000000'
                  AND ten LIKE 'M_c%'
                ORDER BY chuong_id, stt
            """)
            muc_rows = cur.fetchall()
            print(f"   → Tìm được {len(muc_rows)} Mục rows.")

            if not muc_rows:
                print("   Không có dữ liệu để migrate.")
                return

            # ── 3. Thêm cột muc_id vào pddieu (nếu chưa có) ──────────────
            print("[3] Thêm cột muc_id vào pddieu (nếu chưa có)...")
            cur.execute("SHOW COLUMNS FROM pddieu LIKE 'muc_id'")
            if not cur.fetchone():
                if apply:
                    cur.execute("ALTER TABLE pddieu ADD COLUMN muc_id VARCHAR(40) NULL DEFAULT NULL")
                    cur.execute("ALTER TABLE pddieu ADD INDEX idx_muc (muc_id)")
                    conn.commit()
                    print("   → Đã thêm cột muc_id và index.")
                else:
                    print("   [DRY RUN] Sẽ thêm cột muc_id vào pddieu.")
            else:
                print("   → Cột muc_id đã tồn tại, bỏ qua.")

            # ── 4. Insert vào pdmuc ────────────────────────────────────────
            print("[4] Insert dữ liệu vào pdmuc...")
            inserted = 0
            skipped = 0
            for row in muc_rows:
                cur.execute("SELECT 1 FROM pdmuc WHERE mapc = %s", (row["mapc"],))
                if cur.fetchone():
                    skipped += 1
                    continue
                if apply:
                    cur.execute(
                        "INSERT INTO pdmuc (mapc, chuong_id, chimuc, ten, stt) VALUES (%s,%s,%s,%s,%s)",
                        (row["mapc"], row["chuong_id"], row["chimuc"], row["ten"], row["stt"])
                    )
                inserted += 1

            if apply:
                conn.commit()
            print(f"   → Insert: {inserted} | Bỏ qua (đã có): {skipped}")

            # ── 5. Cập nhật muc_id cho từng dieu trong pddieu ─────────────
            print("[5] Cập nhật muc_id cho các điều trong pddieu...")
            updated = 0
            for muc in muc_rows:
                muc_mapc = muc["mapc"]
                chuong_id = muc["chuong_id"]
                # 6 ký tự mã hóa mục trong mapc (vị trí 21-26, 0-indexed)
                muc_part = muc_mapc[20:26]

                # Tất cả điều có cùng chuong_id và cùng muc_part trong mapc
                # nhưng KHÔNG phải chính Mục header đó
                if apply:
                    cur.execute("""
                        UPDATE pddieu
                        SET muc_id = %s
                        WHERE chuong_id = %s
                          AND SUBSTRING(mapc, 21, 6) = %s
                          AND mapc != %s
                    """, (muc_mapc, chuong_id, muc_part, muc_mapc))
                    updated += cur.rowcount
                else:
                    cur.execute("""
                        SELECT COUNT(*) as cnt FROM pddieu
                        WHERE chuong_id = %s
                          AND SUBSTRING(mapc, 21, 6) = %s
                          AND mapc != %s
                    """, (chuong_id, muc_part, muc_mapc))
                    updated += cur.fetchone()["cnt"]

            if apply:
                conn.commit()
            print(f"   → Đã cập nhật muc_id cho {updated} điều.")

            # ── 6. Xóa Mục header rows khỏi pddieu ───────────────────────
            if apply:
                print("[6] Xóa Mục header rows khỏi pddieu...")
                cur.execute("""
                    DELETE FROM pddieu
                    WHERE RIGHT(mapc, 14) = '00000000000000'
                      AND SUBSTRING(mapc, 21, 6) != '000000'
                      AND ten LIKE 'M_c%'
                """)
                deleted = cur.rowcount
                conn.commit()
                print(f"   → Đã xóa {deleted} Mục header rows khỏi pddieu.")
            else:
                print(f"[6] [DRY RUN] Sẽ xóa {len(muc_rows)} Mục header rows khỏi pddieu.")

            # ── Tổng kết ──────────────────────────────────────────────────
            print()
            if apply:
                print("✓ Migration hoàn tất!")
                print(f"  - pdmuc: {inserted} mục")
                print(f"  - pddieu.muc_id: {updated} điều được gán mục")
                print(f"  - pddieu: xóa {len(muc_rows)} header rows")
                print()
                print("Cần rebuild BM25 index sau migration:")
                print("  python scripts/build_bm25_index.py --reset")
            else:
                print("=== DRY RUN — không thay đổi DB ===")
                print(f"  Sẽ tạo bảng pdmuc với {inserted} mục")
                print(f"  Sẽ cập nhật muc_id cho {updated} điều")
                print(f"  Sẽ xóa {len(muc_rows)} Mục header rows khỏi pddieu")
                print()
                print("Chạy lại với --apply để thực hiện:")
                print("  python scripts/migrate_pdmuc.py --apply")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Thực hiện migration (mặc định: dry run)")
    args = parser.parse_args()
    run(apply=args.apply)
