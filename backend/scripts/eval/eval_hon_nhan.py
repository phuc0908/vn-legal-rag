"""
Đánh giá retrieval module Hôn nhân & Gia đình với 4 phương thức:
  1. Vector only       — pure ChromaDB similarity search
  2. Vector + Reranker — ChromaDB → CrossEncoder rerank
  3. Hybrid only       — BM25 + Vector RRF, không rerank
  4. Hybrid + Reranker — BM25 + Vector RRF → CrossEncoder rerank  ← full pipeline

Metrics: Hit@1, Hit@2, Hit@3, Hit@4, Hit@5, Hit@10

Input : backend/data/hon_nhan_data.json  (206 câu)
Output: backend/eval_cache/hon_nhan_report.html

Usage:
    python scripts/eval/eval_hon_nhan.py              # chạy toàn bộ 206 câu
    python scripts/eval/eval_hon_nhan.py --limit 30   # chỉ 30 câu đầu (nhanh hơn)
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

# Hit@K cutoffs — luôn retrieve MAX_RETRIEVE docs để tính đủ tất cả
HIT_AT_KS    = [1, 2, 3, 4, 5, 10]
MAX_RETRIEVE = max(HIT_AT_KS)   # = 10

LIMIT          = None
FORCE_RERANKER = True

METHODS = [
    {"id": "vector",          "label": "Vector only",          "color": "#6b7280"},
    {"id": "vector_rerank",   "label": "Vector + Reranker",    "color": "#2563eb"},
    {"id": "hybrid",          "label": "Hybrid (no rerank)",   "color": "#d97706"},
    {"id": "hybrid_rerank",   "label": "Hybrid + Reranker",    "color": "#16a34a"},
]


# ── Parse args ─────────────────────────────────────────────────────────────────

def parse_args():
    global LIMIT, FORCE_RERANKER
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--limit" and i + 1 < len(args):
            LIMIT = int(args[i + 1])
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
    """Chạy 4 methods, mỗi method lấy MAX_RETRIEVE docs để tính Hit@K đầy đủ."""
    results = {}
    candidate_k = MAX_RETRIEVE * 3   # pool cho reranker (30 docs)

    # 1. Vector only
    vector_docs = rag.vector_store.similarity_search(query, k=MAX_RETRIEVE)
    results["vector"] = vector_docs

    # 2. Vector + Reranker
    if rag.reranker:
        pool = rag.vector_store.similarity_search(query, k=candidate_k)
        results["vector_rerank"] = rag.reranker.rerank(query, pool, top_k=MAX_RETRIEVE)
    else:
        results["vector_rerank"] = vector_docs

    # 3. Hybrid only (no rerank)
    if rag.hybrid_retriever:
        results["hybrid"] = rag.hybrid_retriever.search(query, top_k=MAX_RETRIEVE)
    else:
        results["hybrid"] = vector_docs

    # 4. Hybrid + Reranker
    if rag.hybrid_retriever and rag.reranker:
        pool_h = rag.hybrid_retriever.search(query, top_k=candidate_k)
        results["hybrid_rerank"] = rag.reranker.rerank(query, pool_h, top_k=MAX_RETRIEVE)
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


def hit_at_k(docs: list, dieu_nums: list[str], k: int) -> bool:
    """Trả về True nếu ít nhất 1 doc trong top-k đầu khớp điều tham chiếu."""
    return any(doc_matches_terms(d, dieu_nums) for d in docs[:k])


def first_hit_rank(docs: list, dieu_nums: list[str]) -> int | None:
    """Vị trí (1-based) của doc khớp đầu tiên. None nếu không có trong toàn bộ list."""
    for i, d in enumerate(docs):
        if doc_matches_terms(d, dieu_nums):
            return i + 1
    return None


# ── Build HTML ────────────────────────────────────────────────────────────────

def esc(s: str) -> str:
    return html.escape(str(s))


def build_doc_html(doc: dict, dieu_nums: list[str], rank: int) -> str:
    meta     = doc.get("metadata", {})
    score    = doc.get("score", 0)
    dieu_ten = esc(meta.get("dieu_ten", "—"))
    de_muc   = esc(meta.get("de_muc", ""))
    chuong   = esc(meta.get("chuong_ten", ""))
    content  = esc(doc.get("content", "")[:300])
    matched  = doc_matches_terms(doc, dieu_nums)
    cls      = "doc-row doc-match" if matched else "doc-row"
    badge    = '<span class="match-badge">✓ Khớp</span>' if matched else ''
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


def build_hit_k_row(docs: list, dieu_nums: list[str]) -> str:
    """Thanh Hit@K nhỏ hiển thị trạng thái cho từng cutoff K."""
    rank = first_hit_rank(docs, dieu_nums)
    cells = ""
    for k in HIT_AT_KS:
        matched = rank is not None and rank <= k
        cls  = "hk-yes" if matched else "hk-no"
        icon = "✓" if matched else "✗"
        cells += f'<span class="hk-cell {cls}" title="Hit@{k}">@{k}<br><b>{icon}</b></span>'
    first_txt = f"First: #{rank}" if rank else "Miss"
    return f'<div class="hit-k-row"><span class="hk-label">{first_txt}</span>{cells}</div>'


def build_method_block(method: dict, docs: list, dieu_nums: list[str]) -> str:
    color  = method["color"]
    label  = esc(method["label"])
    rank   = first_hit_rank(docs, dieu_nums)
    hit5   = rank is not None and rank <= 5
    hit_cls = "method-hit" if hit5 else ""

    if rank is not None:
        badge = f'<span class="rank-badge" style="background:{color}">#{rank}</span>'
    else:
        badge = '<span class="rank-badge miss-badge">✗</span>'

    rows = "".join(build_doc_html(d, dieu_nums, i + 1) for i, d in enumerate(docs))
    hit_k_row = build_hit_k_row(docs, dieu_nums)

    return f"""
    <div class="method-block {hit_cls}" style="--method-color:{color}">
      <div class="method-header">
        <span class="method-dot" style="background:{color}"></span>
        <span class="method-name">{label}</span>
        {badge}
      </div>
      {hit_k_row}
      <div class="method-docs">{rows}</div>
    </div>"""


def build_question_card(idx: int, item: dict, all_results: dict) -> str:
    q         = esc(item["question"])
    terms     = esc(item.get("terms", ""))
    dieu_nums = extract_dieu_numbers(item.get("terms", ""))

    # Hit dots — hiển thị hit@5 cho mỗi method (overview nhanh)
    hit_summary = ""
    for m in METHODS:
        docs = all_results.get(m["id"], [])
        rank = first_hit_rank(docs, dieu_nums)
        color = m["color"]
        if rank is not None and rank <= 5:
            label_txt = f"#{rank}"
            dot_cls = ""
        elif rank is not None:
            label_txt = f"@{rank}"
            dot_cls = "dot-late"
        else:
            label_txt = "✗"
            dot_cls = "dot-miss"
        hit_summary += (
            f'<span class="hit-dot {dot_cls}" style="background:{color}" '
            f'title="{esc(m["label"])}">{label_txt}</span>'
        )

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
      <summary>Xem kết quả retrieval ({len(METHODS)} phương thức, top {MAX_RETRIEVE})</summary>
      <div class="methods-grid">{method_blocks}</div>
    </details>
  </div>"""


def build_summary_row(method: dict, all_hits_at_k: dict, total: int) -> str:
    """Một hàng trong bảng tổng hợp: mỗi cột là Hit@K."""
    color = method["color"]
    cells = ""
    for k in HIT_AT_KS:
        hits = all_hits_at_k.get(method["id"], {}).get(k, 0)
        pct  = hits / total * 100 if total else 0
        # Cột @5 và @10 được tô đậm hơn
        bold = ' class="col-bold"' if k in (5, 10) else ''
        cells += f'<td{bold}>{hits}<br><span class="pct">{pct:.1f}%</span></td>'

    # Bar dùng Hit@10
    hits10 = all_hits_at_k.get(method["id"], {}).get(10, 0)
    pct10  = hits10 / total * 100 if total else 0
    bar = f'<div class="bar" style="width:{pct10:.1f}%;background:{color}"></div>'

    return f"""
    <tr>
      <td><span class="dot" style="background:{color}"></span>{esc(method["label"])}</td>
      {cells}
      <td class="bar-cell">{bar}</td>
    </tr>"""


# ── CSS ───────────────────────────────────────────────────────────────────────

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', sans-serif; background: #f3f4f6; color: #111827; font-size: 14px; }
.page { max-width: 1500px; margin: 0 auto; padding: 24px; }
h1 { font-size: 22px; font-weight: 800; color: #1e40af; margin-bottom: 4px; }
.subtitle { color: #6b7280; margin-bottom: 24px; font-size: 13px; }

/* Summary table */
.summary { background: #fff; border-radius: 12px; padding: 20px; margin-bottom: 28px; box-shadow: 0 1px 3px rgba(0,0,0,.1); }
.summary h2 { font-size: 15px; margin-bottom: 14px; color: #374151; }
table { border-collapse: collapse; width: 100%; }
th, td { padding: 8px 12px; text-align: center; border-bottom: 1px solid #e5e7eb; font-size: 13px; }
th:first-child, td:first-child { text-align: left; }
th { background: #f9fafb; font-weight: 600; color: #374151; }
th.col-k5, th.col-k10 { background: #eff6ff; color: #1d4ed8; }
td.col-bold { background: #f0f9ff; font-weight: 600; color: #1e40af; }
.pct { font-size: 11px; color: #6b7280; font-weight: 400; }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }
.bar-cell { width: 180px; }
.bar { height: 14px; border-radius: 3px; min-width: 2px; }

/* Question cards */
.q-card { background: #fff; border-radius: 12px; padding: 16px 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,.1); }
.q-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.q-num { font-weight: 700; color: #1e40af; font-size: 13px; min-width: 28px; }
.q-hits { display: flex; gap: 4px; flex-wrap: wrap; }
.hit-dot { display: inline-flex; align-items: center; justify-content: center;
           min-width: 28px; height: 22px; padding: 0 4px;
           border-radius: 11px; color: #fff; font-size: 11px; font-weight: 700; }
.hit-dot.dot-late { opacity: 0.55; }
.hit-dot.dot-miss { opacity: 0.3; }
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
.rank-badge { display: inline-flex; align-items: center; justify-content: center;
              min-width: 26px; height: 20px; padding: 0 5px;
              border-radius: 10px; color: #fff; font-size: 11px; font-weight: 700; }
.rank-badge.miss-badge { background: #9ca3af !important; }

/* Hit@K row */
.hit-k-row { display: flex; align-items: center; gap: 4px; padding: 6px 12px;
             background: #f9fafb; border-bottom: 1px solid #e5e7eb; flex-wrap: wrap; }
.hk-label { font-size: 11px; color: #6b7280; margin-right: 6px; min-width: 54px; font-weight: 600; }
.hk-cell { display: inline-flex; flex-direction: column; align-items: center;
           width: 34px; padding: 3px 4px; border-radius: 5px;
           font-size: 10px; line-height: 1.3; text-align: center; }
.hk-cell b { font-size: 11px; }
.hk-yes { background: #dcfce7; color: #15803d; }
.hk-no  { background: #f1f5f9; color: #94a3b8; }

/* Doc rows */
.method-docs { padding: 6px 0; }
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


# ── Generate HTML ─────────────────────────────────────────────────────────────

def generate_html(questions: list, all_results_list: list) -> str:
    total = len(questions)

    # Tính Hit@K cho mỗi method
    all_hits_at_k = {m["id"]: {k: 0 for k in HIT_AT_KS} for m in METHODS}
    for item, res in zip(questions, all_results_list):
        dieu_nums = extract_dieu_numbers(item.get("terms", ""))
        for m in METHODS:
            docs = res.get(m["id"], [])
            for k in HIT_AT_KS:
                if hit_at_k(docs, dieu_nums, k):
                    all_hits_at_k[m["id"]][k] += 1

    # Header columns cho mỗi K
    k_headers = "".join(
        f'<th{"  class=\"col-k5\"" if k == 5 else ("  class=\"col-k10\"" if k == 10 else "")}>Hit@{k}</th>'
        for k in HIT_AT_KS
    )
    summary_rows = "".join(build_summary_row(m, all_hits_at_k, total) for m in METHODS)
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
  <p class="subtitle">Tổng {total} câu · retrieve top-{MAX_RETRIEVE} docs mỗi method · Tạo lúc {ts}</p>

  <div class="summary">
    <h2>Hit Rate theo cutoff K (điều tham chiếu xuất hiện trong top-K)</h2>
    <table>
      <thead>
        <tr>
          <th>Phương thức</th>
          {k_headers}
          <th>Biểu đồ (Hit@10)</th>
        </tr>
      </thead>
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

    if FORCE_RERANKER and rag.reranker is None:
        print(f"[RAG] Force-load Reranker: {settings.RERANKER_MODEL}  (cảnh báo: chậm ~50s lần đầu)")
        try:
            rag.reranker = Reranker(settings.RERANKER_MODEL)
        except Exception as e:
            print(f"[RAG] WARNING: Không load được reranker: {e}")

    print(f"[RAG] Sẵn sàng. BM25={rag.hybrid_retriever is not None} | Reranker={rag.reranker is not None}")

    print(f"\n[EVAL] Bắt đầu evaluate {len(questions)} câu × {len(METHODS)} methods × top-{MAX_RETRIEVE}...")
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

    # Summary console
    total = len(questions)
    print(f"\n{'='*70}")
    print(f"{'Phương thức':<30}", end="")
    for k in HIT_AT_KS:
        print(f" Hit@{k:2d}", end="")
    print()
    print("-" * 70)
    for m in METHODS:
        print(f"  {m['label']:<28}", end="")
        for k in HIT_AT_KS:
            hits = sum(
                1 for item, res in zip(questions, all_results_list)
                if hit_at_k(res.get(m["id"], []), extract_dieu_numbers(item.get("terms", "")), k)
            )
            pct = hits / total * 100
            print(f" {pct:5.1f}%", end="")
        print()
    print("=" * 70)


if __name__ == "__main__":
    main()
