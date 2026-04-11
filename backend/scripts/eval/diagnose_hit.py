"""
Chẩn đoán: so sánh cách map ground-truth cũ (regex trên dieu_ten)
với cách mới (query DB qua vbqppl).

Chạy:
    cd backend
    PYTHONIOENCODING=utf-8 python scripts/diagnose_hit.py --sample 20
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

import sys, os, re, json, argparse, random
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, BASE_DIR)
# os.chdir handled by BASE_DIR setup above

from app.db.database import query_all
from app.rag.retrieval import ChromaVectorStore

DATA_PATH = "data/data_tong.json"

# ── Map tên luật trong terms → pattern tìm trong vbqppl ───────────────────

LAW_PATTERNS = [
    # (regex khớp terms, pattern LIKE cho vbqppl, mô tả)
    (r"Luật Hôn nhân và [Gg]ia đình",   "52/2014",      "Luật HN&GĐ 52/2014"),
    (r"Nghị định 126",                   "126/2014",     "NĐ 126/2014"),
    (r"Nghị định 82",                    "82/2020",      "NĐ 82/2020"),
    (r"Nghị định 130",                   "130/2013",     "NĐ 130/2013"),
    (r"Luật Hộ tịch",                    "60/2014",      "Luật Hộ tịch 60/2014"),
    (r"Luật Nuôi con nuôi",              "52/2010",      "Luật NCN 52/2010"),
    (r"Bộ luật Dân sự",                  "91/2015",      "BLDS 91/2015"),
    (r"Bộ luật Hình sự",                 "100/2015",     "BLHS 100/2015"),
]


def parse_terms(terms: str):
    """Trích article numbers và law_pattern từ terms."""
    # "Điều" dùng ký tự Unicode đầy đủ
    nums = re.findall(r'Điều\s+(\d+)', terms)
    if not nums:
        # Fallback: "Theo 33 Luật..."
        nums = re.findall(r'Theo\s+(\d+)\s+Luật', terms)

    law_pattern = None
    law_label = None
    for pattern, vbqppl_key, label in LAW_PATTERNS:
        if re.search(pattern, terms, re.IGNORECASE):
            law_pattern = vbqppl_key
            law_label = label
            break

    return [int(n) for n in nums], law_pattern, law_label


def get_valid_macps_db(article_nums: list, law_pattern: str) -> set:
    """
    Lấy tập mapc hợp lệ từ DB bằng cách query pddieu.vbqppl.
    Trả về set() rỗng nếu không tìm thấy.
    """
    if not article_nums or not law_pattern:
        return set()

    macps = set()
    for num in article_nums:
        rows = query_all(
            "SELECT mapc FROM pddieu WHERE vbqppl LIKE %s AND vbqppl LIKE %s",
            (f"%Điều {num} %", f"%{law_pattern}%")
        )
        for r in rows:
            macps.add(r["mapc"])
    return macps


# ── Cách map CŨ (regex trên dieu_ten) ────────────────────────────────────

def is_hit_old(docs: list, article_nums: list) -> tuple:
    """Logic cũ trong eval_ablation.py."""
    for rank, doc in enumerate(docs, 1):
        dieu_ten = doc.get("metadata", {}).get("dieu_ten", "") or doc.get("metadata", {}).get("tieu_de", "")
        content = doc.get("content", "")
        for num in article_nums:
            if re.search(rf'\.{num}\.', dieu_ten) or re.search(rf'\.{num}\s', dieu_ten):
                return True, rank, dieu_ten
            if re.search(rf'(?:^|\n)Điều {num}[.\s]', content):
                return True, rank, dieu_ten
            if re.search(rf'\bĐiều\s+{num}\b', content):
                return True, rank, dieu_ten
    return False, 0, ""


# ── Cách map MỚI (DB query qua vbqppl) ───────────────────────────────────

def is_hit_db(docs: list, valid_macps: set) -> tuple:
    """So sánh dieu_mapc của doc với tập mapc hợp lệ từ DB."""
    if not valid_macps:
        return None, 0, ""  # không đánh giá được
    for rank, doc in enumerate(docs, 1):
        meta = doc.get("metadata", {})
        doc_mapc = meta.get("dieu_mapc", "")
        if doc_mapc in valid_macps:
            return True, rank, meta.get("dieu_ten") or meta.get("tieu_de", "")
    return False, 0, ""


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)

    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    # Deduplicate
    seen, unique = set(), []
    for item in data:
        q = item["question"].strip()
        if q not in seen:
            seen.add(q); unique.append(item)

    # Chỉ lấy các câu có số điều (dùng Unicode đầy đủ)
    evaluable = [d for d in unique if re.search(r'Điều\s+\d+', d["terms"])]
    samples = random.sample(evaluable, min(args.sample, len(evaluable)))

    print(f"Khởi tạo ChromaVectorStore...")
    vs = ChromaVectorStore()

    print(f"\n{'='*100}")
    print(f"CHẨN ĐOÁN: So sánh cách map ground-truth (cũ vs DB) — {len(samples)} câu")
    print(f"{'='*100}\n")

    agree = 0        # 2 cách đồng ý
    old_only = 0     # chỉ cách cũ nói hit
    db_only = 0      # chỉ cách DB nói hit
    both_miss = 0    # cả 2 miss
    unevaluable = 0  # DB không tìm được mapc

    rows = []
    for i, item in enumerate(samples):
        q = item["question"]
        terms = item["terms"]
        article_nums, law_pattern, law_label = parse_terms(terms)

        if not article_nums:
            continue

        print(f"[{i+1}/{len(samples)}] Query ChromaDB...", end="\r")

        # Retrieve top-5 docs
        docs = vs.similarity_search(q, k=5)

        # Cách cũ
        hit_old, rank_old, matched_ten_old = is_hit_old(docs, article_nums)

        # Cách DB
        valid_macps = get_valid_macps_db(article_nums, law_pattern)
        hit_db, rank_db, matched_ten_db = is_hit_db(docs, valid_macps)

        # Phân loại
        if hit_db is None:
            unevaluable += 1
            status = "⚠️  DB_NOT_FOUND"
        elif hit_old == hit_db:
            agree += 1
            status = "✅ AGREE-HIT" if hit_old else "✅ AGREE-MISS"
        elif hit_old and not hit_db:
            old_only += 1
            status = "🔴 OLD_HIT / DB_MISS  ← old có thể false-positive"
        else:
            db_only += 1
            status = "🟡 OLD_MISS / DB_HIT  ← old bỏ sót"

        rows.append({
            "q": q[:70],
            "terms": terms[:60],
            "article_nums": article_nums,
            "law_label": law_label or "?",
            "valid_macps": list(valid_macps)[:3],
            "status": status,
            "hit_old": hit_old, "rank_old": rank_old, "matched_old": matched_ten_old[:60] if matched_ten_old else "",
            "hit_db": hit_db, "rank_db": rank_db, "matched_db": matched_ten_db[:60] if matched_ten_db else "",
        })

    print(f"\n{'='*100}")
    print(f"{'Câu hỏi':<50} {'Terms':<35} {'Điều':<8} {'Luật':<16} {'Status'}")
    print(f"{'-'*100}")
    for r in rows:
        print(f"{r['q'][:48]:<50} {r['terms'][:33]:<35} {str(r['article_nums']):<8} {r['law_label']:<16} {r['status']}")
        if r["matched_old"]:
            print(f"  {'':50} Old matched: {r['matched_old']}")
        if r["matched_db"]:
            print(f"  {'':50} DB  matched: {r['matched_db']}")
        if r["valid_macps"]:
            print(f"  {'':50} Valid macps: {r['valid_macps']}")
        print()

    n = len(rows)
    print(f"{'='*100}")
    print(f"TỔNG KẾT ({n} câu đánh giá được):")
    print(f"  ✅  Đồng ý (cả hai giống nhau) : {agree:3d} / {n}  ({agree/n*100:.1f}%)")
    print(f"  🔴  Old=HIT  / DB=MISS          : {old_only:3d} / {n}  ({old_only/n*100:.1f}%)  ← old có thể sai")
    print(f"  🟡  Old=MISS / DB=HIT            : {db_only:3d} / {n}  ({db_only/n*100:.1f}%)  ← old bỏ sót")
    print(f"  ⚠️   DB không tìm được mapc       : {unevaluable:3d} câu (terms ngoài HN&GĐ hoặc luật chưa map)")
    print(f"{'='*100}")

    # Tính Hit@5 theo cả 2 cách
    evaluable_both = [r for r in rows if r["hit_db"] is not None]
    if evaluable_both:
        h5_old = sum(1 for r in evaluable_both if r["hit_old"] and r["rank_old"] <= 5) / len(evaluable_both) * 100
        h5_db  = sum(1 for r in evaluable_both if r["hit_db"]  and r["rank_db"]  <= 5) / len(evaluable_both) * 100
        print(f"\nHit@5 baseline (vector search):")
        print(f"  Cách cũ (regex dieu_ten) : {h5_old:.1f}%")
        print(f"  Cách DB (vbqppl mapc)    : {h5_db:.1f}%")
        print(f"  Chênh lệch               : {h5_db - h5_old:+.1f}pp")


if __name__ == "__main__":
    main()
