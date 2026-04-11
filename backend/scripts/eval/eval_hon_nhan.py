"""
Đánh giá retrieval module Hôn nhân & Gia đình với 4 phương thức:
  1. Vector only       — pure ChromaDB similarity search
  2. Vector + Reranker — ChromaDB → CrossEncoder rerank
  3. Hybrid only       — BM25 + Vector RRF, không rerank
  4. Hybrid + Reranker — BM25 + Vector RRF → CrossEncoder rerank  ← full pipeline

Input : backend/data/hon_nhan_data.json  (206 câu)
Output: backend/eval_cache/hon_nhan_report.html

Usage:
    python scripts/eval_hon_nhan.py              # chạy toàn bộ 206 câu
    python scripts/eval_hon_nhan.py --limit 30   # chỉ 30 câu đầu (nhanh hơn)
    python scripts/eval_hon_nhan.py --top-k 5    # số docs mỗi method (mặc định 5)
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

import sys, os, json, re, time, html

sys.path.insert(0, BASE_DIR)

DATA_PATH   = os.path.join(BASE_DIR, "data", "hon_nhan_data.json")
OUTPUT_DIR  = os.path.join(BASE_DIR, "eval_cache")
OUTPUT_HTML = os.path.join(OUTPUT_DIR, "hon_nhan_report.html")

TOP_K = 5
LIMIT = None
FORCE_RERANKER = False

METHODS = [
    {"id": "vector",          "label": "Vector only",          "color": "#6b7280"},
    {"id": "vector_rerank",   "label": "Vector + Reranker",    "color": "#2563eb"},
    {"id": "hybrid",          "label": "Hybrid (no rerank)",   "color": "#d97706"},
    {"id": "hybrid_rerank",   "label": "Hybrid + Reranker",    "color": "#16a34a"},
]


# ── Parse args ─────────────────────────────────────────────────────────────────

def parse_args():
    global TOP_K, LIMIT, FORCE_RERANKER
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--limit" and i + 1 < len(args):
            LIMIT = int(args[i + 1])
        if a == "--top-k" and i + 1 < len(args):
            TOP_K = int(args[i + 1])
        if a == "--with-reranker":
            FORCE_RERANKER = True


# ── Load test data ─────────────────────────────────────────────────────────────

def load_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if LIMIT:
        data = data[:LIMIT]
    print(f"[DATA] Tải {len(data)} câu hỏi từ {DATA_PATH}")
    return data


# ── Retrieve với từng method ──────────────────────────────────────────────────

def retrieve_all_methods(rag, query: str) -> dict:
    """Chạy 4 methods, trả về dict method_id → list of docs."""
    results = {}
    candidate_k = TOP_K * 3   # pool cho reranker

    # 1. Vector only
    vector_docs = rag.vector_store.similarity_search(query, k=TOP_K)
    results["vector"] = vector_docs

    # 2. Vector + Reranker
    if rag.reranker:
        pool = rag.vector_store.similarity_search(query, k=candidate_k)
        results["vector_rerank"] = rag.reranker.rerank(query, pool, top_k=TOP_K)
    else:
        results["vector_rerank"] = vector_docs

    # 3. Hybrid only (no rerank)
    if rag.hybrid_retriever:
        results["hybrid"] = rag.hybrid_retriever.search(query, top_k=TOP_K)
    else:
        results["hybrid"] = vector_docs

    # 4. Hybrid + Reranker
    if rag.hybrid_retriever and rag.reranker:
        pool_h = rag.hybrid_retriever.search(query, top_k=candidate_k)
        results["hybrid_rerank"] = rag.reranker.rerank(query, pool_h, top_k=TOP_K)
    elif rag.reranker:
        results["hybrid_rerank"] = results["vector_rerank"]
    else:
        results["hybrid_rerank"] = results["hybrid"]

    return results


# ── Tìm điều số từ chuỗi "terms" ─────────────────────────────────────────────

def extract_dieu_numbers(terms: str) -> list[str]:
    """Trích xuất tất cả số điều từ chuỗi terms. Ví dụ: 'Điều 31, 82' → ['31','82']"""
    nums = re.findall(r'\b(\d{1,3})\b', terms)
    return list(set(nums))


def doc_matches_terms(doc: dict, dieu_nums: list[str]) -> bool:
    """Kiểm tra doc có chứa điều số nào trong expected list không."""
    if not dieu_nums:
        return False
    meta = doc.get("metadata", {})
    dieu_ten = meta.get("dieu_ten", "")
    dieu_so  = meta.get("dieu_so", "")
    content  = doc.get("content", "")
    combined = f"{dieu_ten} {dieu_so} {content[:200]}"
    return any(re.search(rf'\b{n}\b', combined) for n in dieu_nums)


# ── Build HTML ────────────────────────────────────────────────────────────────

def esc(s: str) -> str:
    return html.escape(str(s))


def build_doc_html(doc: dict, dieu_nums: list[str], rank: int) -> str:
    meta    = doc.get("metadata", {})
    score   = doc.get("score", 0)
    dieu_ten= esc(meta.get("dieu_ten", "—"))
    de_muc  = esc(meta.get("de_muc", ""))
    chuong  = esc(meta.get("chuong_ten", ""))
    content = esc(doc.get("content", "")[:300])
    matched = doc_matches_terms(doc, dieu_nums)
    cls     = "doc-row doc-match" if matched else "doc-row"
    badge   = '<span class="match-badge">✓ Khớp</span>' if matched else ''
    return f"""
    <div class="{cls}">
      <div class="doc-rank">#{rank}</div>
      <div class="doc-body">
        <div class="doc-title">{dieu_ten} {badge}</div>
        <div class="doc-meta">{de_muc}{' · ' + chuong if chuong else ''}</div>
        <div class="doc-content">{content}…</div>
      </div>
      <div class="doc-score">{score:.4f}</div>
    </div>"""


def build_method_block(method: dict, docs: list, dieu_nums: list[str]) -> str:
    color   = method["color"]
    label   = esc(method["label"])
    hit     = any(doc_matches_terms(d, dieu_nums) for d in docs)
    hit_cls = "method-hit" if hit else ""
    hit_txt = "✓" if hit else "✗"
    rows    = "".join(build_doc_html(d, dieu_nums, i+1) for i, d in enumerate(docs))
    return f"""
    <div class="method-block {hit_cls}" style="--method-color:{color}">
      <div class="method-header">
        <span class="method-dot" style="background:{color}"></span>
        <span class="method-name">{label}</span>
        <span class="method-hit-icon">{hit_txt}</span>
      </div>
      <div class="method-docs">{rows}</div>
    </div>"""


def build_question_card(idx: int, item: dict, all_results: dict) -> str:
    q        = esc(item["question"])
    terms    = esc(item.get("terms", ""))
    dieu_nums= extract_dieu_numbers(item.get("terms", ""))

    # hit count per method
    hit_summary = ""
    for m in METHODS:
        docs = all_results.get(m["id"], [])
        hit  = any(doc_matches_terms(d, dieu_nums) for d in docs)
        color= m["color"]
        icon = "✓" if hit else "✗"
        hit_summary += f'<span class="hit-dot" style="background:{color}" title="{esc(m["label"])}">{icon}</span>'

    method_blocks = "".join(
        build_method_block(m, all_results.get(m["id"], []), dieu_nums)
        for m in METHODS
    )

    return f"""
  <div class="q-card" id="q{idx}">
    <div class="q-header">
      <span class="q-num">#{idx + 1}</span>
      <div class="q-hits">{hit_summary}</div>
    </div>
    <div class="q-text">{q}</div>
    <div class="q-terms">📌 {terms}</div>
    <details class="q-methods">
      <summary>Xem kết quả retrieval ({len(METHODS)} phương thức, top {TOP_K})</summary>
      <div class="methods-grid">{method_blocks}</div>
    </details>
  </div>"""


def build_summary_row(method: dict, all_hits: dict, total: int) -> str:
    hits = all_hits.get(method["id"], 0)
    pct  = hits / total * 100 if total else 0
    bar  = f'<div class="bar" style="width:{pct:.1f}%;background:{method["color"]}"></div>'
    return f"""
    <tr>
      <td><span class="dot" style="background:{method["color"]}"></span>{esc(method["label"])}</td>
      <td>{hits} / {total}</td>
      <td>{pct:.1f}%</td>
      <td class="bar-cell">{bar}</td>
    </tr>"""


CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', sans-serif; background: #f3f4f6; color: #111827; font-size: 14px; }
.page { max-width: 1400px; margin: 0 auto; padding: 24px; }
h1 { font-size: 22px; font-weight: 800; color: #1e40af; margin-bottom: 4px; }
.subtitle { color: #6b7280; margin-bottom: 24px; font-size: 13px; }

/* Summary table */
.summary { background: #fff; border-radius: 12px; padding: 20px; margin-bottom: 28px; box-shadow: 0 1px 3px rgba(0,0,0,.1); }
.summary h2 { font-size: 15px; margin-bottom: 14px; color: #374151; }
table { border-collapse: collapse; width: 100%; }
th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #e5e7eb; font-size: 13px; }
th { background: #f9fafb; font-weight: 600; color: #374151; }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }
.bar-cell { width: 200px; }
.bar { height: 14px; border-radius: 3px; min-width: 2px; }

/* Question cards */
.q-card { background: #fff; border-radius: 12px; padding: 16px 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,.1); }
.q-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.q-num { font-weight: 700; color: #1e40af; font-size: 13px; min-width: 28px; }
.q-hits { display: flex; gap: 4px; }
.hit-dot { display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 50%; color: #fff; font-size: 11px; font-weight: 700; }
.q-text { font-size: 14px; line-height: 1.6; color: #111827; margin-bottom: 6px; }
.q-terms { font-size: 12px; color: #1d4ed8; background: #eff6ff; padding: 4px 10px; border-radius: 6px; display: inline-block; margin-bottom: 10px; }

/* Collapsible methods */
details > summary { cursor: pointer; font-size: 13px; color: #6b7280; padding: 4px 0; user-select: none; }
details > summary:hover { color: #374151; }
.methods-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-top: 12px; }
@media (max-width: 900px) { .methods-grid { grid-template-columns: 1fr; } }

/* Method blocks */
.method-block { border: 2px solid #e5e7eb; border-radius: 8px; overflow: hidden; }
.method-block.method-hit { border-color: var(--method-color); }
.method-header { display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: #f9fafb; border-bottom: 1px solid #e5e7eb; }
.method-block.method-hit .method-header { background: color-mix(in srgb, var(--method-color) 10%, white); }
.method-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.method-name { font-weight: 600; font-size: 12px; color: #374151; flex: 1; }
.method-hit-icon { font-size: 13px; font-weight: 700; color: var(--method-color); }
.method-docs { padding: 6px 0; }

/* Doc rows */
.doc-row { display: flex; align-items: flex-start; gap: 8px; padding: 8px 12px; border-bottom: 1px solid #f3f4f6; }
.doc-row:last-child { border-bottom: none; }
.doc-row.doc-match { background: #f0fdf4; }
.doc-rank { flex-shrink: 0; width: 20px; font-size: 11px; color: #9ca3af; padding-top: 2px; }
.doc-body { flex: 1; min-width: 0; }
.doc-title { font-size: 12px; font-weight: 600; color: #1f2937; line-height: 1.4; }
.doc-meta { font-size: 11px; color: #6b7280; margin: 1px 0; }
.doc-content { font-size: 11px; color: #6b7280; line-height: 1.45; margin-top: 2px; white-space: pre-wrap; word-break: break-word; }
.doc-score { flex-shrink: 0; font-size: 11px; font-weight: 600; color: #6b7280; text-align: right; padding-top: 2px; }
.match-badge { display: inline-block; background: #16a34a; color: #fff; font-size: 10px; padding: 1px 5px; border-radius: 3px; margin-left: 4px; vertical-align: middle; }
"""


def generate_html(questions: list, all_results_list: list) -> str:
    total = len(questions)

    # Count hits per method
    all_hits = {m["id"]: 0 for m in METHODS}
    for item, res in zip(questions, all_results_list):
        dieu_nums = extract_dieu_numbers(item.get("terms", ""))
        for m in METHODS:
            if any(doc_matches_terms(d, dieu_nums) for d in res.get(m["id"], [])):
                all_hits[m["id"]] += 1

    summary_rows = "".join(build_summary_row(m, all_hits, total) for m in METHODS)
    question_cards = "".join(
        build_question_card(i, item, res)
        for i, (item, res) in enumerate(zip(questions, all_results_list))
    )

    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Eval: Hôn nhân & Gia đình — {ts}</title>
<style>{CSS}</style>
</head>
<body>
<div class="page">
  <h1>Đánh giá Retrieval — Module Hôn nhân & Gia đình</h1>
  <p class="subtitle">Tổng {total} câu · top-{TOP_K} docs mỗi method · Tạo lúc {ts}</p>

  <div class="summary">
    <h2>Tổng hợp Hit Rate (điều tham chiếu xuất hiện trong kết quả)</h2>
    <table>
      <thead><tr><th>Phương thức</th><th>Hit / Total</th><th>Hit Rate</th><th>Biểu đồ</th></tr></thead>
      <tbody>{summary_rows}</tbody>
    </table>
  </div>

  <div class="q-list">
{question_cards}
  </div>
</div>
</body>
</html>"""


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parse_args()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    questions = load_data()

    print("[RAG] Tải hon_nhan RAG system...")
    from app.rag.retrieval import get_hon_nhan_rag_system, Reranker
    from app.core.config import settings
    rag = get_hon_nhan_rag_system()

    # Force-load reranker nếu dùng flag --with-reranker
    if FORCE_RERANKER and rag.reranker is None:
        print(f"[RAG] Force-load Reranker: {settings.RERANKER_MODEL}  (cảnh báo: chậm ~50s lần đầu)")
        try:
            rag.reranker = Reranker(settings.RERANKER_MODEL)
        except Exception as e:
            print(f"[RAG] WARNING: Không load được reranker: {e}")

    print(f"[RAG] Sẵn sàng. BM25={rag.hybrid_retriever is not None} | Reranker={rag.reranker is not None}")

    print(f"\n[EVAL] Bắt đầu evaluate {len(questions)} câu × {len(METHODS)} methods...")
    all_results_list = []
    t_start = time.time()

    for i, item in enumerate(questions):
        t0 = time.time()
        res = retrieve_all_methods(rag, item["question"])
        all_results_list.append(res)
        elapsed = time.time() - t0
        if (i + 1) % 10 == 0 or i == 0:
            total_elapsed = time.time() - t_start
            eta = total_elapsed / (i + 1) * (len(questions) - i - 1)
            print(f"  [{i+1:3d}/{len(questions)}] {elapsed:.1f}s/câu | ETA={eta:.0f}s")

    print(f"\n[HTML] Đang tạo report...")
    html_content = generate_html(questions, all_results_list)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)

    size_kb = os.path.getsize(OUTPUT_HTML) / 1024
    print(f"[DONE] Report: {OUTPUT_HTML} ({size_kb:.0f} KB)")
    print(f"[DONE] Tổng thời gian: {time.time()-t_start:.1f}s")

    # Quick summary
    total = len(questions)
    print("\n=== HIT RATE SUMMARY ===")
    for m in METHODS:
        hits = sum(
            1 for item, res in zip(questions, all_results_list)
            if any(doc_matches_terms(d, extract_dieu_numbers(item.get("terms","")))
                   for d in res.get(m["id"], []))
        )
        print(f"  {m['label']:30s}: {hits:3d}/{total} = {hits/total*100:.1f}%")


if __name__ == "__main__":
    main()
