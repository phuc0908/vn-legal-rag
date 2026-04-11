"""
Ablation Study — Đánh giá hệ thống RAG pháp luật Việt Nam
==========================================================
Sử dụng tập dữ liệu hôn nhân (data/data_tong.json) làm ground-truth.

Các cấu hình so sánh:
  baseline     — Vector search thuần (ChromaDB), không rerank, không rewrite
  +rerank      — Vector search + CrossEncoder reranking
  +hybrid      — Hybrid (BM25 + Vector RRF), không rerank
  +hybrid+rr   — Hybrid + CrossEncoder reranking
  +full        — Hybrid + CrossEncoder + query rewriting (LLM)

Metrics (retrieval):
  Hit@1, Hit@3, Hit@5  — tỷ lệ câu hỏi có doc đúng trong top-k
  MRR                  — Mean Reciprocal Rank

Metrics (generation, chỉ config full):
  ROUGE-L              — Độ tương đồng câu trả lời với đáp án chuẩn

Cách dùng:
  cd backend
  # chỉ đánh giá retrieval (nhanh, không cần LLM)
  python scripts/eval_ablation.py --sample 200

  # đánh giá cả retrieval + generation (cần GROQ_API_KEY)
  python scripts/eval_ablation.py --sample 200 --eval-gen 50

  # dùng toàn bộ dataset
  python scripts/eval_ablation.py --sample 0

Kết quả lưu tại: scripts/eval_cache/ablation_results.json
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
import json
import time
import random
import argparse
from typing import Optional

# Fix Windows terminal encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stderr.reconfigure(encoding='utf-8')

# Thêm thư mục gốc backend vào path
sys.path.insert(0, BASE_DIR)
# os.chdir handled by BASE_DIR setup above

CACHE_DIR = os.path.join(_SCRIPTS_DIR, "eval_cache")
DATA_PATH = os.path.join(BASE_DIR, "data", "data_tong.json")

# ── Map tên luật thường gặp → số hiệu để query vbqppl ───────────────────────
# Dùng khi terms không có số hiệu trực tiếp (vd: "Luật Hôn nhân và gia đình 2014")
LAW_NAME_TO_SO_HIEU = {
    # Hôn nhân gia đình
    r"hôn nhân và gia đình":     "52/2014",
    r"hôn nhân gia đình":        "52/2014",
    r"\bHNGĐ\b":                 "52/2014",
    r"\bHN&GĐ\b":                "52/2014",
    # Bộ luật Dân sự
    r"bộ luật dân sự":           "91/2015",
    r"\bBLDS\b":                 "91/2015",
    # Bộ luật Hình sự
    r"bộ luật hình sự":          "100/2015",
    r"\bBLHS\b":                 "100/2015",
    r"sửa đổi bộ luật hình sự":  "92/2017",
    # Giao thông
    r"giao thông đường bộ\b(?!.*\d{4}/\d{4})": "23/2008",
    # Hộ tịch
    r"luật hộ tịch":             "60/2014",
    # Nuôi con nuôi
    r"nuôi con nuôi":            "52/2010",
    # Cư trú
    r"luật cư trú":              "68/2020",
    # Căn cước công dân
    r"căn cước công dân":        "59/2014",
    # Nghĩa vụ quân sự
    r"nghĩa vụ quân sự":         "78/2015",
    # Hàng hải
    r"bộ luật hàng hải":         "95/2015",
    # Xử lý vi phạm hành chính
    r"xử lý vi phạm hành chính": "15/2012",
}


def _parse_terms(terms: str):
    """
    Trích từ chuỗi terms:
      - article_nums: list[int] — các số điều
      - so_hieu: str | None     — số hiệu văn bản để LIKE trong vbqppl

    Ưu tiên: số hiệu trực tiếp (dd/yyyy/loại) > map tên luật.
    """
    # 1. Số điều
    nums = re.findall(r'Điều\s+(\d+)', terms)
    if not nums:
        nums = re.findall(r'Theo\s+(\d+)\s+Luật', terms)
    article_nums = [int(n) for n in nums]

    # 2. Số hiệu trực tiếp — dd/yyyy/loai
    m = re.search(r'(\d+/\d{4}/[\w-]+)', terms)
    if m:
        return article_nums, m.group(1)

    # 3. Map tên luật
    terms_lower = terms.lower()
    for pattern, so_hieu in LAW_NAME_TO_SO_HIEU.items():
        if re.search(pattern, terms_lower, re.IGNORECASE):
            return article_nums, so_hieu

    return article_nums, None


# ── Cache ground-truth từ DB (tránh query lặp) ───────────────────────────────
_gt_cache: dict = {}


def get_ground_truth(article_nums: list, so_hieu: str) -> dict:
    """
    Query pddieu dùng CẢ HAI cột vbqppl (số điều + số hiệu) và ten (tên điều).
    Trả về dict {mapc: ten} — rỗng nếu không tìm thấy.

    Dùng hai cột để đảm bảo chính xác:
      - vbqppl: xác định đây là điều luật đúng trong văn bản gốc
      - ten   : xác nhận tên điều khớp với ChromaDB metadata
    """
    if not article_nums or not so_hieu:
        return {}

    cache_key = (tuple(sorted(article_nums)), so_hieu)
    if cache_key in _gt_cache:
        return _gt_cache[cache_key]

    from app.db.database import query_all
    gt = {}  # {mapc: ten}
    for num in article_nums:
        rows = query_all(
            # Lọc theo vbqppl (số điều + số hiệu văn bản) → lấy cả mapc và ten
            "SELECT mapc, ten FROM pddieu WHERE vbqppl LIKE %s AND vbqppl LIKE %s",
            (f"%Điều {num} %", f"%{so_hieu}%"),
        )
        for r in rows:
            gt[r["mapc"]] = r["ten"]

    _gt_cache[cache_key] = gt
    return gt


def is_hit(docs: list, ground_truth: dict, rank_limit: int = 5):
    """
    Kiểm tra doc trong top rank_limit có khớp ground-truth không.
    Một doc được tính là HIT khi THỎA MÃN ÍT NHẤT MỘT trong hai điều kiện:
      1. dieu_mapc khớp với mapc trong DB (từ vbqppl)   — điều kiện chính
      2. dieu_ten  khớp với ten  trong DB (từ cột ten)  — điều kiện xác nhận

    Cả hai điều kiện đều dùng dữ liệu từ pddieu, nên nhất quán và chính xác.
    Trả về (hit: bool, rank: int, method: str).
    """
    if not ground_truth:
        return None, 0, ""

    valid_macps = set(ground_truth.keys())
    valid_tens  = set(ground_truth.values())

    for rank, doc in enumerate(docs[:rank_limit], 1):
        meta = doc.get("metadata", {})
        doc_mapc = meta.get("dieu_mapc", "")
        doc_ten  = meta.get("dieu_ten", "")

        # Điều kiện 1: mapc khớp (từ vbqppl query)
        if doc_mapc and doc_mapc in valid_macps:
            return True, rank, "mapc"

        # Điều kiện 2: ten khớp (từ cột ten query) — bắt được doc bị mismatch mapc
        if doc_ten and doc_ten in valid_tens:
            return True, rank, "ten"

    return False, 0, ""


def compute_mrr(ranks: list) -> float:
    """Mean Reciprocal Rank từ list rank (0 = miss)."""
    reciprocals = [1.0 / r for r in ranks if r > 0]
    return sum(reciprocals) / len(ranks) if ranks else 0.0


def rouge_l(hypothesis: str, reference: str) -> float:
    """ROUGE-L đơn giản dùng LCS (không cần thư viện ngoài)."""
    h_tokens = hypothesis.lower().split()
    r_tokens = reference.lower().split()
    if not h_tokens or not r_tokens:
        return 0.0
    # LCS
    m, n = len(r_tokens), len(h_tokens)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if r_tokens[i - 1] == h_tokens[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    lcs = dp[m][n]
    precision = lcs / n if n else 0
    recall = lcs / m if m else 0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


# ── Khởi tạo các component ───────────────────────────────────────────────────

def init_components(enable_reranker: bool = True, enable_llm: bool = True):
    """Khởi tạo tất cả component RAG. Trả về dict các component."""
    from app.core.config import settings
    from app.rag.retrieval import ChromaVectorStore, BM25Index, HybridRetriever

    print("\n[INIT] Đang khởi tạo ChromaVectorStore...")
    vector_store = ChromaVectorStore()

    print("[INIT] Đang load BM25 index...")
    bm25 = BM25Index(settings.BM25_INDEX_PATH)
    bm25_ok = bm25.load()
    if not bm25_ok:
        print(f"[WARN] BM25 index không tồn tại tại '{settings.BM25_INDEX_PATH}'")
        print("[WARN] Chạy: python scripts/build_bm25_index.py để build")

    hybrid = HybridRetriever(vector_store, bm25) if bm25_ok else None

    reranker = None
    if enable_reranker:
        try:
            from app.rag.retrieval import Reranker
            print(f"[INIT] Đang load Reranker '{settings.RERANKER_MODEL}'...")
            reranker = Reranker(settings.RERANKER_MODEL)
        except Exception as e:
            print(f"[WARN] Không load được Reranker: {e}")

    llm_manager = None
    if enable_llm:
        try:
            from app.rag.llm import get_llm_manager
            print("[INIT] Đang khởi tạo LLM manager...")
            llm_manager = get_llm_manager()
            if llm_manager:
                print("[INIT] LLM sẵn sàng.")
            else:
                print("[WARN] LLM manager không khởi tạo được (thiếu API key?)")
        except Exception as e:
            print(f"[WARN] Lỗi khởi tạo LLM: {e}")

    return {
        "vector_store": vector_store,
        "bm25": bm25 if bm25_ok else None,
        "hybrid": hybrid,
        "reranker": reranker,
        "llm_manager": llm_manager,
    }


# ── Đánh giá retrieval (tối ưu: cache embedding, chỉ gọi ChromaDB 1-2 lần/câu) ──

CANDIDATE_MULT = 3  # lấy nhiều hơn để rerank


def _rrf_merge(vector_docs: list, bm25_docs: list, top_k: int, rrf_k: int = 60) -> list:
    """Reciprocal Rank Fusion — dùng lại logic từ HybridRetriever."""
    scores: dict = {}
    by_id: dict = {}

    def doc_id(doc):
        return doc.get("metadata", {}).get("dieu_mapc") or doc["content"][:50]

    for rank, doc in enumerate(vector_docs):
        did = doc_id(doc)
        scores[did] = scores.get(did, 0.0) + 1.0 / (rrf_k + rank + 1)
        by_id[did] = doc
    for rank, doc in enumerate(bm25_docs):
        did = doc_id(doc)
        scores[did] = scores.get(did, 0.0) + 1.0 / (rrf_k + rank + 1)
        if did not in by_id:
            by_id[did] = doc

    sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)
    result = []
    for did in sorted_ids[:top_k]:
        result.append({**by_id[did], "score": scores[did]})
    return result


def evaluate_retrieval(samples: list, components: dict, top_k: int = 5) -> dict:
    """
    Chạy 5 config trên tập samples, tính Hit@1/3/5 và MRR.
    Tối ưu: gọi ChromaDB 1-2 lần/câu (cache kết quả embedding), mô phỏng
    tất cả config từ cùng một pool kết quả thô.
    """
    vs = components["vector_store"]
    bm25 = components.get("bm25")
    reranker = components.get("reranker")
    llm_manager = components.get("llm_manager")

    cfg_names = ["baseline", "+rerank", "+hybrid", "+hybrid+rr", "+full"]
    results = {name: {"hits": {1: [], 3: [], 5: []}, "ranks": []} for name in cfg_names}
    results["+full"]["rewrites"] = []

    # per-sample details cho HTML report
    per_sample: list = []

    total = len(samples)
    evaluable = 0

    large_k = top_k * CANDIDATE_MULT  # pool lớn dùng cho reranking

    for i, item in enumerate(samples):
        question = item["question"]
        terms = item["terms"]
        article_nums, so_hieu = _parse_terms(terms)

        if not article_nums:
            continue

        # Lấy ground-truth từ DB (vbqppl + ten) — đây là ground-truth chính xác
        ground_truth = get_ground_truth(article_nums, so_hieu)
        if not ground_truth:
            # Không map được → bỏ qua (không thể đánh giá)
            continue
        evaluable += 1

        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/{total}] ({evaluable} evaluable)...")

        # ── Query rewriting cho config full ──
        rewritten = question
        if llm_manager:
            try:
                rewritten = llm_manager.rewrite_query(question)
            except Exception:
                pass

        # ── 1 lần gọi ChromaDB với large_k (dùng chung cho cả 5 config) ──
        try:
            vec_large = vs.similarity_search(question, k=large_k)
        except Exception as e:
            print(f"  [ERR] ChromaDB error q{i}: {e}")
            for name in cfg_names:
                for k in [1, 3, 5]:
                    results[name]["hits"][k].append(0)
                results[name]["ranks"].append(0)
            continue

        # ── BM25 (1 lần, nếu có) ──
        bm25_large = bm25.search(question, top_k=large_k) if bm25 else []

        # ── Query rewriting: lấy thêm vector results cho rewritten query ──
        vec_rewritten = []
        if rewritten != question:
            try:
                vec_rewritten = vs.similarity_search(rewritten, k=large_k)
            except Exception:
                vec_rewritten = vec_large  # fallback
        else:
            vec_rewritten = vec_large

        # ── BM25 cho rewritten query ──
        bm25_rewritten = bm25.search(rewritten, top_k=large_k) if bm25 else []

        # ── Tổng hợp kết quả từng config ──
        config_docs = {}

        # baseline: top_k từ vector search (không rerank)
        config_docs["baseline"] = vec_large[:top_k]

        # +rerank: large pool vector → rerank → top_k
        if reranker:
            config_docs["+rerank"] = reranker.rerank(question, list(vec_large), top_k)
        else:
            config_docs["+rerank"] = vec_large[:top_k]

        # +hybrid: RRF vector + BM25, không rerank
        if bm25_large:
            config_docs["+hybrid"] = _rrf_merge(vec_large, bm25_large, top_k)
        else:
            config_docs["+hybrid"] = vec_large[:top_k]

        # +hybrid+rr: RRF (large) → rerank → top_k
        if bm25_large:
            hybrid_large = _rrf_merge(vec_large, bm25_large, large_k)
        else:
            hybrid_large = list(vec_large)
        if reranker:
            config_docs["+hybrid+rr"] = reranker.rerank(question, hybrid_large, top_k)
        else:
            config_docs["+hybrid+rr"] = hybrid_large[:top_k]

        # +full: rewritten query → RRF (large) → rerank → top_k
        if bm25_rewritten:
            hybrid_rewritten_large = _rrf_merge(vec_rewritten, bm25_rewritten, large_k)
        else:
            hybrid_rewritten_large = list(vec_rewritten)
        if reranker:
            config_docs["+full"] = reranker.rerank(rewritten, hybrid_rewritten_large, top_k)
        else:
            config_docs["+full"] = hybrid_rewritten_large[:top_k]

        # ── Ghi kết quả ──
        sample_record = {
            "question": question,
            "terms": terms,
            "article_nums": article_nums,
            "so_hieu": so_hieu,
            "valid_macps": list(ground_truth.keys()),
            "valid_tens": list(ground_truth.values()),
            "rewritten": rewritten if rewritten != question else None,
            "configs": {},
        }
        for name in cfg_names:
            docs = config_docs.get(name, [])
            hit, rank, method = is_hit(docs, ground_truth, rank_limit=top_k)
            if hit is None:
                continue
            for k in [1, 3, 5]:
                results[name]["hits"][k].append(1 if (hit and rank <= k) else 0)
            results[name]["ranks"].append(rank if hit else 0)
            # Lưu top-3 doc titles để hiện thị trong report
            top_docs = [
                {
                    "dieu_ten": d.get("metadata", {}).get("dieu_ten", ""),
                    "chu_de": d.get("metadata", {}).get("chu_de", ""),
                    "score": round(float(d.get("score", 0)), 4),
                }
                for d in docs[:3]
            ]
            sample_record["configs"][name] = {
                "hit": bool(hit),
                "rank": rank,
                "method": method,  # "mapc" | "ten" | "" — cách nào matched
                "top_docs": top_docs,
            }

        results["+full"]["rewrites"].append(rewritten != question)
        per_sample.append(sample_record)

    # ── Tổng hợp metrics ──
    summary = {}
    for name in cfg_names:
        r = results[name]
        n = len(r["ranks"])
        if n == 0:
            summary[name] = {"n": 0}
            continue
        summary[name] = {
            "n": n,
            "hit@1": round(sum(r["hits"][1]) / n * 100, 1),
            "hit@3": round(sum(r["hits"][3]) / n * 100, 1),
            "hit@5": round(sum(r["hits"][5]) / n * 100, 1),
            "mrr": round(compute_mrr(r["ranks"]), 4),
        }
        if name == "+full" and r.get("rewrites"):
            summary[name]["rewrite_rate"] = round(
                sum(r["rewrites"]) / len(r["rewrites"]) * 100, 1
            )

    summary["_meta"] = {
        "total_samples": total,
        "evaluable": evaluable,
        "top_k": top_k,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    summary["_per_sample"] = per_sample

    return summary


# ── Đánh giá generation (ROUGE-L) ────────────────────────────────────────────

def evaluate_generation(samples: list, components: dict, top_k: int = 5) -> dict:
    """
    Chạy full pipeline (retrieval + LLM generation) trên tập samples nhỏ.
    Tính ROUGE-L giữa câu trả lời sinh ra và đáp án chuẩn.
    Yêu cầu LLM manager.
    """
    llm_manager = components.get("llm_manager")
    if not llm_manager:
        print("[SKIP] Bỏ qua đánh giá generation — LLM chưa cấu hình")
        return {}

    from app.rag.pipeline import get_rag_pipeline
    from app.models.schemas import QueryRequest

    pipeline = get_rag_pipeline()
    scores = []
    results = []

    print(f"\n[GEN EVAL] Đánh giá generation trên {len(samples)} câu hỏi...")
    for i, item in enumerate(samples):
        question = item["question"]
        expected = item["answer"]
        print(f"  [{i+1}/{len(samples)}] Q: {question[:60]}...")
        try:
            req = QueryRequest(query=question, top_k=top_k)
            resp = pipeline.process_query(req)
            generated = resp.answer
            score = rouge_l(generated, expected)
            scores.append(score)
            results.append({
                "question": question,
                "expected": expected[:200],
                "generated": generated[:200],
                "rouge_l": round(score, 4),
                "terms": item["terms"],
            })
            print(f"         ROUGE-L: {score:.4f}")
        except Exception as e:
            print(f"  [ERR] {e}")
            scores.append(0)
        time.sleep(0.5)  # tránh rate limit

    return {
        "avg_rouge_l": round(sum(scores) / len(scores), 4) if scores else 0,
        "n": len(scores),
        "samples": results,
    }


# ── In bảng kết quả ──────────────────────────────────────────────────────────

CONFIG_ORDER = ["baseline", "+rerank", "+hybrid", "+hybrid+rr", "+full"]
CONFIG_LABELS = {
    "baseline":     "Baseline (Vector)",
    "+rerank":      "+ CrossEncoder Rerank",
    "+hybrid":      "+ Hybrid (BM25+Vec)",
    "+hybrid+rr":   "+ Hybrid + Rerank",
    "+full":        "+ Full (Hybrid+RR+Rewrite)",
}


def print_retrieval_table(summary: dict):
    meta = summary.get("_meta", {})
    print("\n" + "=" * 72)
    print("  ABLATION STUDY — RETRIEVAL METRICS")
    print(f"  Dataset: {meta.get('evaluable', '?')} câu hỏi có số điều | top_k={meta.get('top_k', 5)}")
    print(f"  Thời điểm: {meta.get('timestamp', '')}")
    print("=" * 72)
    header = f"{'Cấu hình':<30} {'Hit@1':>7} {'Hit@3':>7} {'Hit@5':>7} {'MRR':>8}"
    print(header)
    print("-" * 72)
    for cfg in CONFIG_ORDER:
        if cfg not in summary:
            continue
        m = summary[cfg]
        if m.get("n", 0) == 0:
            print(f"  {'(không có dữ liệu)':<28}")
            continue
        label = CONFIG_LABELS.get(cfg, cfg)
        row = (f"  {label:<28} "
               f"{m['hit@1']:>6.1f}% "
               f"{m['hit@3']:>6.1f}% "
               f"{m['hit@5']:>6.1f}% "
               f"{m['mrr']:>8.4f}")
        print(row)
    print("=" * 72)


def print_generation_table(gen_results: dict):
    if not gen_results:
        return
    print("\n" + "=" * 72)
    print("  GENERATION QUALITY — ROUGE-L")
    print(f"  Số câu đánh giá: {gen_results.get('n', 0)}")
    print(f"  Average ROUGE-L: {gen_results.get('avg_rouge_l', 0):.4f}")
    print("=" * 72)
    for s in gen_results.get("samples", [])[:5]:
        print(f"\n  Q: {s['question'][:70]}")
        print(f"  Expected: {s['expected'][:100]}")
        print(f"  Generated: {s['generated'][:100]}")
        print(f"  ROUGE-L: {s['rouge_l']}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Ablation study cho hệ thống RAG pháp luật Việt Nam"
    )
    parser.add_argument(
        "--sample", type=int, default=200,
        help="Số câu hỏi ngẫu nhiên để đánh giá (0 = toàn bộ dataset)"
    )
    parser.add_argument(
        "--eval-gen", type=int, default=0,
        help="Số câu đánh giá generation với LLM (0 = bỏ qua)"
    )
    parser.add_argument(
        "--top-k", type=int, default=5,
        help="Số doc lấy ra (default: 5)"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed để tái lập kết quả"
    )
    parser.add_argument(
        "--no-reranker", action="store_true",
        help="Tắt reranker (tăng tốc)"
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Lưu kết quả JSON ra file (mặc định: eval_cache/ablation_results.json)"
    )
    args = parser.parse_args()

    random.seed(args.seed)

    # Load dataset
    print(f"[DATA] Đang đọc {DATA_PATH}...")
    if not os.path.exists(DATA_PATH):
        print(f"[ERR] Không tìm thấy file: {DATA_PATH}")
        sys.exit(1)
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    print(f"[DATA] Tổng số records: {len(data)}")

    # Loại bỏ duplicate questions (giữ record đầu tiên)
    seen = set()
    unique_data = []
    for item in data:
        q = item["question"].strip()
        if q not in seen:
            seen.add(q)
            unique_data.append(item)
    print(f"[DATA] Sau khi loại duplicate: {len(unique_data)} câu hỏi")

    # Lọc những câu có số điều rõ ràng (pre-filter nhanh trước khi query DB)
    evaluable = [d for d in unique_data if _parse_terms(d["terms"])[0]]
    print(f"[DATA] Có số điều trong terms: {len(evaluable)} câu")
    print(f"[DATA] (Lọc chính xác bằng DB vbqppl sẽ diễn ra trong quá trình eval)")

    # Sample
    if args.sample > 0 and args.sample < len(evaluable):
        samples = random.sample(evaluable, args.sample)
        print(f"[DATA] Sử dụng {len(samples)} câu ngẫu nhiên (seed={args.seed})")
    else:
        samples = evaluable
        print(f"[DATA] Sử dụng toàn bộ {len(samples)} câu")

    # Khởi tạo components
    enable_llm = args.eval_gen > 0
    components = init_components(
        enable_reranker=not args.no_reranker,
        enable_llm=enable_llm,
    )

    # Đánh giá retrieval
    print(f"\n[EVAL] Bắt đầu đánh giá retrieval ({len(samples)} câu, top_k={args.top_k})...")
    t_start = time.time()
    retrieval_summary = evaluate_retrieval(samples, components, top_k=args.top_k)
    elapsed = time.time() - t_start
    print(f"[EVAL] Hoàn tất trong {elapsed:.1f}s")

    print_retrieval_table(retrieval_summary)

    # Đánh giá generation (tuỳ chọn)
    gen_results = {}
    if args.eval_gen > 0:
        gen_samples = random.sample(
            evaluable, min(args.eval_gen, len(evaluable))
        )
        gen_results = evaluate_generation(gen_samples, components, top_k=args.top_k)
        print_generation_table(gen_results)

    # Lưu kết quả
    os.makedirs(CACHE_DIR, exist_ok=True)
    out_path = args.output or os.path.join(CACHE_DIR, "ablation_results.json")
    output = {
        "retrieval": retrieval_summary,
        "generation": gen_results,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[SAVE] Kết quả đã lưu tại: {out_path}")


if __name__ == "__main__":
    main()
