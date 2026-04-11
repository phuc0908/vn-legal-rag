"""
Tạo HTML report chi tiết từ kết quả ablation study.

Cách dùng:
    cd backend
    python scripts/generate_report.py
    # → mở file: scripts/eval_cache/report.html

Tuỳ chọn:
    python scripts/generate_report.py --input scripts/eval_cache/ablation_results.json
                                      --output scripts/eval_cache/report.html
"""

import sys
import os
import json
import argparse
from datetime import datetime

# Fix Windows encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = _SCRIPTS_DIR
DEFAULT_INPUT = os.path.join(SCRIPT_DIR, "eval_cache", "ablation_results.json")
DEFAULT_OUTPUT = os.path.join(SCRIPT_DIR, "eval_cache", "report.html")

CONFIG_LABELS = {
    "baseline":     "Baseline (Vector Search)",
    "+rerank":      "+ CrossEncoder Rerank",
    "+hybrid":      "+ Hybrid BM25+Vector",
    "+hybrid+rr":   "+ Hybrid + Rerank",
    "+full":        "+ Full Pipeline",
}
CONFIG_DESCRIPTIONS = {
    "baseline":     "Tìm kiếm vector thuần — embed câu hỏi → cosine similarity với ChromaDB (241k docs). Không có bước hậu xử lý.",
    "+rerank":      "Lấy 15 candidates từ vector search, sau đó dùng CrossEncoder (AITeamVN/Vietnamese_Reranker) để sắp xếp lại theo độ liên quan ngữ nghĩa.",
    "+hybrid":      "Kết hợp BM25 (keyword) và vector search bằng Reciprocal Rank Fusion (RRF, k=60). BM25 giúp bắt các từ khoá pháp lý chính xác (số điều, tên luật).",
    "+hybrid+rr":   "Hybrid BM25+Vector lấy 15 candidates, sau đó CrossEncoder reranking để chọn top-5 chính xác nhất.",
    "+full":        "Pipeline đầy đủ: LLM viết lại câu hỏi thành truy vấn pháp lý chuẩn → Hybrid search → CrossEncoder reranking. Đây là cấu hình production.",
}
CONFIG_COLORS = {
    "baseline":     "#6b7280",
    "+rerank":      "#3b82f6",
    "+hybrid":      "#10b981",
    "+hybrid+rr":   "#f59e0b",
    "+full":        "#ef4444",
}
CONFIG_ORDER = ["baseline", "+rerank", "+hybrid", "+hybrid+rr", "+full"]


def load_data(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def pct(v) -> str:
    if v is None:
        return "—"
    return f"{v:.1f}%"


def delta_html(val: float, baseline: float) -> str:
    """Hiển thị delta so với baseline với màu."""
    if baseline is None or val is None:
        return ""
    d = val - baseline
    if abs(d) < 0.05:
        return '<span class="delta-neutral">±0</span>'
    color = "delta-up" if d > 0 else "delta-down"
    sign = "+" if d > 0 else ""
    return f'<span class="{color}">{sign}{d:.1f}pp</span>'


def build_chart_data(retrieval: dict) -> dict:
    """Chuẩn bị data cho Chart.js."""
    labels = []
    hit1, hit3, hit5, mrr_vals = [], [], [], []
    colors = []
    for cfg in CONFIG_ORDER:
        m = retrieval.get(cfg, {})
        if not m or m.get("n", 0) == 0:
            continue
        labels.append(CONFIG_LABELS.get(cfg, cfg))
        hit1.append(m.get("hit@1", 0))
        hit3.append(m.get("hit@3", 0))
        hit5.append(m.get("hit@5", 0))
        mrr_vals.append(round(m.get("mrr", 0) * 100, 1))
        colors.append(CONFIG_COLORS.get(cfg, "#888"))
    return {
        "labels": labels,
        "hit1": hit1,
        "hit3": hit3,
        "hit5": hit5,
        "mrr": mrr_vals,
        "colors": colors,
    }


def sample_rows_html(per_sample: list, cfg_order: list) -> str:
    if not per_sample:
        return "<p class='muted'>Không có dữ liệu per-sample. Chạy lại eval để có chi tiết.</p>"

    rows = []
    for idx, s in enumerate(per_sample):
        question = s.get("question", "")
        terms = s.get("terms", "")
        article_nums = s.get("article_nums", [])
        rewritten = s.get("rewritten")
        configs = s.get("configs", {})

        # Màu nền luân phiên
        row_class = "row-even" if idx % 2 == 0 else "row-odd"

        config_cells = ""
        for cfg in cfg_order:
            c = configs.get(cfg, {})
            if not c:
                config_cells += "<td>—</td>"
                continue
            hit = c.get("hit", False)
            rank = c.get("rank", 0)
            method = c.get("method", "")
            top_docs = c.get("top_docs", [])
            hit_icon = "✅" if hit else "❌"
            method_badge = f'<span class="method-badge">{method}</span>' if hit and method else ""
            rank_str = f"@{rank}" if hit else "miss"
            doc_list = "".join(
                f'<div class="doc-item">'
                f'<span class="doc-rank">#{i+1}</span> '
                f'<span class="doc-name">{d["dieu_ten"][:60] or "(không tên)"}</span>'
                f'<span class="doc-score"> [{d["score"]}]</span>'
                f'</div>'
                for i, d in enumerate(top_docs)
            )
            tooltip = f'<div class="tooltip-content">{doc_list}</div>' if doc_list else ""
            cell_class = "hit-yes" if hit else "hit-no"
            config_cells += (
                f'<td class="{cell_class}">'
                f'<div class="hit-tooltip">'
                f'{hit_icon} <code>{rank_str}</code> {method_badge}'
                f'{tooltip}'
                f'</div>'
                f'</td>'
            )

        rewrite_row = (
            f'<div class="rewrite-tag">✏️ Rewrite: <em>{rewritten[:80]}</em></div>'
            if rewritten else ""
        )

        rows.append(f"""
        <tr class="{row_class}">
            <td class="q-cell">
                <div class="q-text">{question}</div>
                <div class="terms-tag">📖 {terms}</div>
                <div class="art-tag">Điều: {', '.join(str(n) for n in article_nums)}</div>
                {rewrite_row}
            </td>
            {config_cells}
        </tr>""")

    headers = "".join(
        f'<th style="background:{CONFIG_COLORS.get(c,"#888")}">{CONFIG_LABELS.get(c,c)}</th>'
        for c in cfg_order
    )

    return f"""
    <div class="table-scroll">
    <table class="sample-table">
        <thead>
            <tr>
                <th>Câu hỏi / Điều luật cần tìm</th>
                {headers}
            </tr>
        </thead>
        <tbody>
            {"".join(rows)}
        </tbody>
    </table>
    </div>"""


def generation_section_html(gen: dict) -> str:
    if not gen or not gen.get("n"):
        return """
        <div class="card warn-card">
            <h3>⚠️ Chưa có dữ liệu đánh giá Generation</h3>
            <p>Chạy lại với cờ <code>--eval-gen 50</code> để đánh giá chất lượng câu trả lời:</p>
            <pre>PYTHONIOENCODING=utf-8 python scripts/eval_ablation.py --sample 100 --eval-gen 50</pre>
        </div>"""

    avg = gen.get("avg_rouge_l", 0)
    n = gen.get("n", 0)
    samples = gen.get("samples", [])

    sample_rows = ""
    for s in samples[:10]:
        rl = s.get("rouge_l", 0)
        bar_w = int(rl * 100)
        color = "#10b981" if rl >= 0.3 else "#f59e0b" if rl >= 0.15 else "#ef4444"
        sample_rows += f"""
        <tr>
            <td class="q-cell">{s.get('question','')[:80]}</td>
            <td class="terms-small">{s.get('terms','')[:50]}</td>
            <td>{s.get('expected','')[:100]}</td>
            <td>{s.get('generated','')[:100]}</td>
            <td class="center">
                <div class="rouge-bar-wrap">
                    <div class="rouge-bar" style="width:{bar_w}%;background:{color}"></div>
                    <span>{rl:.3f}</span>
                </div>
            </td>
        </tr>"""

    return f"""
    <div class="card">
        <h2>📝 Generation Quality — ROUGE-L</h2>
        <div class="metric-row">
            <div class="big-metric">
                <span class="big-num">{avg:.4f}</span>
                <span class="big-label">Average ROUGE-L</span>
            </div>
            <div class="big-metric">
                <span class="big-num">{n}</span>
                <span class="big-label">Câu hỏi đánh giá</span>
            </div>
        </div>
        <h3>Chi tiết từng câu (top 10)</h3>
        <div class="table-scroll">
        <table class="gen-table">
            <thead>
                <tr>
                    <th>Câu hỏi</th>
                    <th>Điều luật</th>
                    <th>Đáp án chuẩn</th>
                    <th>Câu trả lời sinh ra</th>
                    <th>ROUGE-L</th>
                </tr>
            </thead>
            <tbody>{sample_rows}</tbody>
        </table>
        </div>
    </div>"""


def generate_html(data: dict, output_path: str):
    retrieval = data.get("retrieval", {})
    generation = data.get("generation", {})
    meta = retrieval.get("_meta", {})
    per_sample = retrieval.get("_per_sample", [])

    ts = meta.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    n_eval = meta.get("evaluable", "?")
    top_k = meta.get("top_k", 5)
    total = meta.get("total_samples", "?")

    chart = build_chart_data(retrieval)

    # Baseline values for delta
    base = retrieval.get("baseline", {})
    base_h1 = base.get("hit@1")
    base_h3 = base.get("hit@3")
    base_h5 = base.get("hit@5")
    base_mrr = base.get("mrr")

    # ── Bảng metrics ──
    table_rows = ""
    for i, cfg in enumerate(CONFIG_ORDER):
        m = retrieval.get(cfg, {})
        if not m or m.get("n", 0) == 0:
            continue
        h1 = m.get("hit@1")
        h3 = m.get("hit@3")
        h5 = m.get("hit@5")
        mrr = m.get("mrr")
        color = CONFIG_COLORS.get(cfg, "#888")
        label = CONFIG_LABELS.get(cfg, cfg)
        is_best_h1 = h1 == max(r.get("hit@1", 0) for c, r in retrieval.items() if not c.startswith("_"))
        is_best_h5 = h5 == max(r.get("hit@5", 0) for c, r in retrieval.items() if not c.startswith("_"))

        rr = m.get("rewrite_rate")
        rr_badge = f'<span class="badge">{rr}% rewritten</span>' if rr is not None else ""

        table_rows += f"""
        <tr>
            <td>
                <span class="cfg-dot" style="background:{color}"></span>
                <strong>{label}</strong>
                {rr_badge}
                <div class="cfg-desc">{CONFIG_DESCRIPTIONS.get(cfg,"")}</div>
            </td>
            <td class="metric {'best' if is_best_h1 else ''}">{pct(h1)} {delta_html(h1, base_h1) if i>0 else ''}</td>
            <td class="metric">{pct(h3)} {delta_html(h3, base_h3) if i>0 else ''}</td>
            <td class="metric {'best' if is_best_h5 else ''}">{pct(h5)} {delta_html(h5, base_h5) if i>0 else ''}</td>
            <td class="metric">{mrr:.4f} {delta_html(mrr*100 if mrr else None, base_mrr*100 if base_mrr else None) if i>0 else ''}</td>
        </tr>"""

    gen_html = generation_section_html(generation)
    sample_html = sample_rows_html(per_sample, CONFIG_ORDER)

    # Chart JSON
    chart_json = json.dumps(chart, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VN Legal RAG — Ablation Study Report</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  :root {{
    --bg: #f8fafc; --card: #fff; --border: #e2e8f0;
    --text: #1e293b; --muted: #64748b; --accent: #3b82f6;
    --hit-yes: #dcfce7; --hit-no: #fee2e2;
    --up: #16a34a; --down: #dc2626;
  }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); font-size: 14px; }}

  .page-header {{
    background: linear-gradient(135deg, #1e40af 0%, #3b82f6 50%, #0ea5e9 100%);
    color: #fff; padding: 40px 48px; position: relative; overflow: hidden;
  }}
  .page-header::after {{
    content: "⚖️"; font-size: 120px; position: absolute; right: 40px; top: -10px;
    opacity: 0.15; line-height: 1;
  }}
  .page-header h1 {{ font-size: 28px; font-weight: 700; margin-bottom: 6px; }}
  .page-header p  {{ opacity: 0.85; font-size: 14px; }}
  .header-meta {{ display: flex; gap: 24px; margin-top: 20px; flex-wrap: wrap; }}
  .header-badge {{
    background: rgba(255,255,255,0.2); border-radius: 20px;
    padding: 4px 14px; font-size: 13px; font-weight: 600;
  }}

  .container {{ max-width: 1400px; margin: 0 auto; padding: 32px 24px; }}

  .card {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; padding: 28px 32px; margin-bottom: 28px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }}
  .card h2 {{ font-size: 18px; font-weight: 700; margin-bottom: 20px; color: var(--text); }}
  .card h3 {{ font-size: 15px; font-weight: 600; margin: 20px 0 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; }}
  .warn-card {{ border-color: #fbbf24; background: #fffbeb; }}
  .warn-card h3 {{ color: #92400e; }}

  .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-bottom: 24px; }}
  .stat-box {{
    border: 1px solid var(--border); border-radius: 10px;
    padding: 16px 20px; text-align: center;
  }}
  .stat-val {{ font-size: 28px; font-weight: 800; color: var(--accent); line-height: 1; }}
  .stat-label {{ font-size: 12px; color: var(--muted); margin-top: 6px; text-transform: uppercase; letter-spacing: 0.05em; }}

  /* Metrics table */
  .metrics-table {{ width: 100%; border-collapse: collapse; }}
  .metrics-table th {{
    background: #f1f5f9; text-align: left; padding: 10px 16px;
    font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em;
    color: var(--muted); border-bottom: 2px solid var(--border);
  }}
  .metrics-table td {{ padding: 14px 16px; border-bottom: 1px solid var(--border); vertical-align: top; }}
  .metrics-table tr:hover td {{ background: #f8fafc; }}
  .metric {{ text-align: center; font-size: 16px; font-weight: 700; white-space: nowrap; }}
  .metric.best {{ color: #16a34a; background: #f0fdf4; border-radius: 6px; }}
  .cfg-dot {{
    display: inline-block; width: 10px; height: 10px;
    border-radius: 50%; margin-right: 8px; vertical-align: middle;
  }}
  .cfg-desc {{ font-size: 12px; color: var(--muted); margin-top: 4px; line-height: 1.5; }}
  .delta-up   {{ color: var(--up); font-size: 11px; font-weight: 600; margin-left: 4px; }}
  .delta-down {{ color: var(--down); font-size: 11px; font-weight: 600; margin-left: 4px; }}
  .delta-neutral {{ color: var(--muted); font-size: 11px; margin-left: 4px; }}
  .badge {{
    display: inline-block; background: #ede9fe; color: #7c3aed;
    border-radius: 12px; padding: 1px 8px; font-size: 11px; font-weight: 600;
    margin-left: 8px; vertical-align: middle;
  }}

  /* Charts */
  .charts-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
  .chart-box {{
    border: 1px solid var(--border); border-radius: 10px;
    padding: 20px; background: #fafafa;
  }}
  .chart-box h4 {{ font-size: 13px; font-weight: 600; color: var(--muted); margin-bottom: 16px; text-transform: uppercase; }}
  @media (max-width: 900px) {{ .charts-grid {{ grid-template-columns: 1fr; }} }}

  /* Sample table */
  .table-scroll {{ overflow-x: auto; border-radius: 8px; border: 1px solid var(--border); }}
  .sample-table, .gen-table {{ width: 100%; border-collapse: collapse; min-width: 900px; }}
  .sample-table th, .gen-table th {{
    background: #1e293b; color: #fff; padding: 10px 14px;
    font-size: 12px; text-align: left; white-space: nowrap;
  }}
  .sample-table td, .gen-table td {{ padding: 10px 14px; border-bottom: 1px solid var(--border); vertical-align: top; }}
  .row-even {{ background: #fff; }}
  .row-odd  {{ background: #f8fafc; }}
  .q-cell {{ max-width: 340px; min-width: 220px; }}
  .q-text  {{ font-size: 13px; line-height: 1.5; margin-bottom: 6px; }}
  .terms-tag {{ font-size: 11px; color: #2563eb; margin-top: 4px; }}
  .art-tag   {{ font-size: 11px; color: #7c3aed; font-weight: 600; }}
  .rewrite-tag {{ font-size: 11px; color: #0369a1; margin-top: 4px; }}
  .terms-small {{ font-size: 11px; color: var(--muted); max-width: 140px; }}

  /* Hit cells */
  .hit-yes {{ background: var(--hit-yes); }}
  .hit-no  {{ background: var(--hit-no); }}
  .hit-tooltip {{ position: relative; cursor: help; text-align: center; font-size: 13px; }}
  .hit-tooltip .tooltip-content {{
    display: none; position: absolute; left: 50%; transform: translateX(-50%);
    top: 110%; z-index: 99; background: #1e293b; color: #fff;
    padding: 10px 14px; border-radius: 8px; min-width: 280px;
    font-size: 11px; line-height: 1.6; white-space: normal;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  }}
  .hit-tooltip:hover .tooltip-content {{ display: block; }}
  .doc-item {{ margin-bottom: 4px; }}
  .doc-rank  {{ color: #94a3b8; margin-right: 4px; }}
  .doc-name  {{ color: #e2e8f0; }}
  .doc-score {{ color: #fbbf24; }}
  .method-badge {{
    display: inline-block; font-size: 9px; font-weight: 700;
    padding: 1px 5px; border-radius: 4px; margin-left: 2px; vertical-align: middle;
    background: #dbeafe; color: #1d4ed8; text-transform: uppercase; letter-spacing: 0.04em;
  }}

  /* Generation */
  .metric-row {{ display: flex; gap: 32px; margin-bottom: 24px; flex-wrap: wrap; }}
  .big-metric {{ text-align: center; }}
  .big-num   {{ display: block; font-size: 36px; font-weight: 800; color: var(--accent); }}
  .big-label {{ display: block; font-size: 12px; color: var(--muted); text-transform: uppercase; }}
  .rouge-bar-wrap {{ display: flex; align-items: center; gap: 8px; min-width: 120px; }}
  .rouge-bar {{ height: 8px; border-radius: 4px; min-width: 2px; }}

  /* Methodology */
  .method-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }}
  .method-card {{
    border: 1px solid var(--border); border-radius: 10px; padding: 18px;
    border-left: 4px solid var(--accent);
  }}
  .method-card h4 {{ font-size: 13px; font-weight: 700; margin-bottom: 8px; }}
  .method-card p  {{ font-size: 12px; color: var(--muted); line-height: 1.6; }}

  .muted {{ color: var(--muted); }}
  .legend {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; }}
  .legend-item {{ display: flex; align-items: center; gap: 6px; font-size: 12px; }}
  .legend-dot {{ width: 12px; height: 12px; border-radius: 3px; flex-shrink: 0; }}

  footer {{ text-align: center; padding: 32px; color: var(--muted); font-size: 12px; }}
  pre {{ background: #f1f5f9; padding: 12px 16px; border-radius: 6px; font-size: 12px; overflow-x: auto; }}
  code {{ background: #f1f5f9; padding: 1px 5px; border-radius: 4px; font-size: 12px; }}
  .section-divider {{
    display: flex; align-items: center; gap: 12px; margin: 12px 0 20px;
    color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em;
  }}
  .section-divider::before, .section-divider::after {{
    content: ""; flex: 1; height: 1px; background: var(--border);
  }}
</style>
</head>
<body>

<!-- HEADER -->
<div class="page-header">
  <h1>📊 Ablation Study — VN Legal RAG</h1>
  <p>Đánh giá hệ thống hỏi đáp pháp luật Việt Nam theo từng thành phần kỹ thuật</p>
  <div class="header-meta">
    <span class="header-badge">📅 {ts}</span>
    <span class="header-badge">🗄️ Dataset: Luật Hôn nhân &amp; Gia đình</span>
    <span class="header-badge">📌 n = {n_eval} câu | Top-K = {top_k}</span>
    <span class="header-badge">🔢 Tổng corpus: 241,429 docs</span>
  </div>
</div>

<div class="container">

<!-- STATS -->
<div class="card">
  <h2>📋 Tổng quan Dataset</h2>
  <div class="stats-grid">
    <div class="stat-box">
      <div class="stat-val">{total}</div>
      <div class="stat-label">Tổng câu hỏi</div>
    </div>
    <div class="stat-box">
      <div class="stat-val">{n_eval}</div>
      <div class="stat-label">Câu có thể đánh giá<br><small>(có số điều rõ ràng)</small></div>
    </div>
    <div class="stat-box">
      <div class="stat-val">{top_k}</div>
      <div class="stat-label">Top-K retrieval</div>
    </div>
    <div class="stat-box">
      <div class="stat-val">241k</div>
      <div class="stat-label">Docs trong ChromaDB</div>
    </div>
    <div class="stat-box">
      <div class="stat-val">5</div>
      <div class="stat-label">Cấu hình so sánh</div>
    </div>
    <div class="stat-box">
      <div class="stat-val">3</div>
      <div class="stat-label">Retrieval metrics<br><small>(Hit@1/3/5, MRR)</small></div>
    </div>
  </div>
  <div style="background:#eff6ff;border-radius:8px;padding:14px 18px;font-size:13px;color:#1d4ed8;margin-top:4px;">
    <strong>Ground-truth:</strong> mỗi câu hỏi có nhãn <em>điều luật cần tìm</em> (từ trường <code>terms</code> trong dataset).
    Hệ thống được đánh giá là <strong>Hit</strong> khi tìm được đúng điều luật đó trong top-K kết quả trả về.
    Dataset nguồn: <code>data/data_tong.json</code> — chủ đề Hôn nhân &amp; Gia đình.
  </div>
</div>

<!-- METRICS TABLE -->
<div class="card">
  <h2>🎯 Kết quả Retrieval — So sánh 5 Cấu hình</h2>

  <div class="section-divider">Bảng kết quả</div>
  <div class="legend">
    {"".join(f'<span class="legend-item"><span class="legend-dot" style="background:{CONFIG_COLORS.get(c,"#888")}"></span>{CONFIG_LABELS.get(c,c)}</span>' for c in CONFIG_ORDER if retrieval.get(c,{}).get("n",0)>0)}
    <span class="legend-item" style="margin-left:auto;font-size:11px;color:var(--muted)">
      <span style="color:#16a34a">●</span> Tốt nhất trong cột &nbsp;|&nbsp;
      <span class="delta-up">+Xpp</span> Cải thiện so với baseline &nbsp;|&nbsp;
      <span class="delta-down">−Xpp</span> Giảm so với baseline
    </span>
  </div>

  <table class="metrics-table">
    <thead>
      <tr>
        <th style="width:38%">Cấu hình</th>
        <th style="width:14%;text-align:center">Hit@1 ↑</th>
        <th style="width:14%;text-align:center">Hit@3 ↑</th>
        <th style="width:14%;text-align:center">Hit@5 ↑</th>
        <th style="width:20%;text-align:center">MRR ↑</th>
      </tr>
    </thead>
    <tbody>
      {table_rows}
    </tbody>
  </table>

  <div style="margin-top:14px;font-size:12px;color:var(--muted)">
    <strong>Hit@K</strong>: tỷ lệ % câu hỏi mà điều luật đúng xuất hiện trong Top-K kết quả.&nbsp;
    <strong>MRR</strong> (Mean Reciprocal Rank): trung bình của 1/rank — cao hơn khi điều luật đúng xuất hiện ở vị trí cao hơn.&nbsp;
    <strong>pp</strong> = percentage points.
  </div>
</div>

<!-- CHARTS -->
<div class="card">
  <h2>📈 Biểu đồ so sánh</h2>
  <div class="charts-grid">
    <div class="chart-box">
      <h4>Hit@1 / Hit@3 / Hit@5 (%)</h4>
      <canvas id="chartHit" height="220"></canvas>
    </div>
    <div class="chart-box">
      <h4>MRR × 100 (điểm càng cao càng tốt)</h4>
      <canvas id="chartMRR" height="220"></canvas>
    </div>
  </div>
</div>

<!-- GENERATION -->
{gen_html}

<!-- PER-SAMPLE -->
<div class="card">
  <h2>🔍 Chi tiết từng câu hỏi</h2>
  <p style="color:var(--muted);font-size:13px;margin-bottom:16px;">
    Di chuột vào ô ✅/❌ để xem top-3 documents được retrieve.
    <code>@N</code> = điều luật đúng nằm ở vị trí N.
  </p>
  {sample_html}
</div>

<!-- METHODOLOGY -->
<div class="card">
  <h2>🛠️ Phương pháp — Kiến trúc từng cấu hình</h2>
  <div class="method-grid">
    {"".join(f'''
    <div class="method-card" style="border-left-color:{CONFIG_COLORS.get(c,"#888")}">
      <h4><span style="color:{CONFIG_COLORS.get(c,"#888")}">●</span> {CONFIG_LABELS.get(c,c)}</h4>
      <p>{CONFIG_DESCRIPTIONS.get(c,"")}</p>
    </div>''' for c in CONFIG_ORDER)}
  </div>

  <div class="section-divider" style="margin-top:28px">Công nghệ sử dụng</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-top:4px">
    {"".join(f'<div style="background:#f8fafc;border:1px solid var(--border);border-radius:8px;padding:12px 16px;font-size:12px;"><strong>{k}</strong><br><span style="color:var(--muted)">{v}</span></div>' for k,v in [
        ("Embedding Model","AITeamVN/Vietnamese_Embedding"),
        ("Vector Store","ChromaDB (HNSW index)"),
        ("BM25 Library","rank_bm25 (BM25Okapi)"),
        ("Fusion","Reciprocal Rank Fusion k=60"),
        ("Reranker","AITeamVN/Vietnamese_Reranker"),
        ("LLM (Rewrite)","Groq — Llama3-8b-8192"),
        ("Framework","FastAPI + LangChain"),
        ("Dataset","data_tong.json (Luật HN&GĐ)"),
    ])}
  </div>
</div>

</div><!-- end container -->

<footer>
  VN Legal RAG — Đồ án Tốt nghiệp &nbsp;|&nbsp; Generated {ts} &nbsp;|&nbsp;
  <code>python scripts/generate_report.py</code>
</footer>

<script>
const chartData = {chart_json};

const commonOpts = {{
  responsive: true,
  plugins: {{
    legend: {{ position: 'bottom', labels: {{ font: {{ size: 11 }} }} }},
    tooltip: {{ callbacks: {{ label: ctx => ` ${{ctx.dataset.label}}: ${{ctx.parsed.y.toFixed(1)}}` }} }}
  }},
  scales: {{
    y: {{ beginAtZero: true, max: 100, ticks: {{ font: {{ size: 11 }} }} }},
    x: {{ ticks: {{ font: {{ size: 10 }}, maxRotation: 20 }} }}
  }}
}};

// Hit chart (grouped bar)
new Chart(document.getElementById('chartHit'), {{
  type: 'bar',
  data: {{
    labels: chartData.labels,
    datasets: [
      {{
        label: 'Hit@1',
        data: chartData.hit1,
        backgroundColor: chartData.colors.map(c => c + 'cc'),
        borderColor: chartData.colors,
        borderWidth: 2,
        borderRadius: 4,
      }},
      {{
        label: 'Hit@3',
        data: chartData.hit3,
        backgroundColor: chartData.colors.map(c => c + '88'),
        borderColor: chartData.colors,
        borderWidth: 2,
        borderRadius: 4,
        borderDash: [4,4],
      }},
      {{
        label: 'Hit@5',
        data: chartData.hit5,
        backgroundColor: chartData.colors.map(c => c + '44'),
        borderColor: chartData.colors,
        borderWidth: 2,
        borderRadius: 4,
      }},
    ]
  }},
  options: {{...commonOpts}}
}});

// MRR chart
new Chart(document.getElementById('chartMRR'), {{
  type: 'bar',
  data: {{
    labels: chartData.labels,
    datasets: [{{
      label: 'MRR × 100',
      data: chartData.mrr,
      backgroundColor: chartData.colors.map(c => c + 'bb'),
      borderColor: chartData.colors,
      borderWidth: 2,
      borderRadius: 6,
    }}]
  }},
  options: {{...commonOpts, scales: {{
    y: {{ beginAtZero: true, max: 100, ticks: {{ font: {{ size: 11 }} }} }},
    x: {{ ticks: {{ font: {{ size: 10 }}, maxRotation: 20 }} }}
  }}}}
}});
</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK] Report đã lưu tại: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Sinh HTML report từ ablation results")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="File JSON kết quả")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="File HTML output")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"[ERR] Không tìm thấy: {args.input}")
        print("Chạy eval trước: python scripts/eval_ablation.py --sample 100")
        sys.exit(1)

    print(f"[READ] {args.input}")
    data = load_data(args.input)
    out = generate_html(data, args.output)
    print(f"[DONE] Mở file trong trình duyệt: {out}")


if __name__ == "__main__":
    main()
