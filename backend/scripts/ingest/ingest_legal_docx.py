"""
Chunk Bộ luật theo Điều (Article-level chunking).
Mỗi Điều = 1 chunk. Nếu Điều quá dài (>1000 tokens) thì split theo Khoản.

Metadata mỗi chunk:
  - source, doc_name, part, chapter, chapter_title
  - article_num, article_title, chunk_type ("full" | "khoan")
  - khoan_num (nếu chunk_type == "khoan")
  - chunk_index, total_chars

Usage:
    python ingest_legal_docx.py
    python ingest_legal_docx.py data/my_law.docx
"""

import sys
import os
import io
import re
import json
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, _SCRIPTS_DIR)

from docx import Document

# ── Patterns ────────────────────────────────────────────────────────────────

RE_PHAN   = re.compile(r"^Phần\s+(.+)$", re.IGNORECASE)
RE_CHUONG = re.compile(r"^Chương\s+([IVXLCDM\d]+)\s*$", re.IGNORECASE)
RE_DIEU   = re.compile(r"^Điều\s+(\d+)[\.\[\d]?\s*(.*)", re.UNICODE)
RE_KHOAN  = re.compile(r"^\d+\.\s+", re.UNICODE)   # "1. ", "2. " ...

MAX_CHARS = 2000  # Ngưỡng để split theo Khoản (~1000 tokens tiếng Việt)


# ── Parser ───────────────────────────────────────────────────────────────────

def parse_articles(docx_path: str) -> list[dict]:
    """
    Đọc file .docx và trả về list các article dict:
    {
        part, chapter, chapter_title,
        article_num, article_title, content,
        raw_lines: [...]
    }
    """
    doc = Document(docx_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    articles = []
    current_part = ""
    current_chapter = ""
    current_chapter_title = ""
    pending_chapter = False   # True khi vừa gặp "Chương X", chờ dòng tiếp là title

    current_article = None

    for i, line in enumerate(paragraphs):
        # Phần
        m_phan = RE_PHAN.match(line)
        if m_phan:
            current_part = line
            pending_chapter = False
            continue

        # Chương
        m_chuong = RE_CHUONG.match(line)
        if m_chuong:
            current_chapter = line
            pending_chapter = True
            continue

        # Dòng tiếp sau "Chương X" là tên chương
        if pending_chapter:
            current_chapter_title = line
            pending_chapter = False
            continue

        # Điều
        m_dieu = RE_DIEU.match(line)
        if m_dieu:
            # Lưu article cũ
            if current_article is not None:
                articles.append(current_article)

            article_num = m_dieu.group(1)
            # Tên điều có thể nằm sau số hoặc rỗng (tên ở dòng tiếp)
            article_title_inline = m_dieu.group(2).strip()
            # Làm sạch: bỏ [1], [2] footnote
            article_title_inline = re.sub(r"\[\d+\]", "", article_title_inline).strip()

            current_article = {
                "part": current_part,
                "chapter": current_chapter,
                "chapter_title": current_chapter_title,
                "article_num": article_num,
                "article_title": article_title_inline,
                "raw_lines": [],
            }
            continue

        # Nội dung thuộc Điều hiện tại
        if current_article is not None:
            # Tên điều đôi khi ở dòng ngay sau "Điều X."
            if not current_article["article_title"] and not current_article["raw_lines"]:
                current_article["article_title"] = re.sub(r"\[\d+\]", "", line).strip()
            else:
                current_article["raw_lines"].append(line)

    # Lưu article cuối
    if current_article is not None:
        articles.append(current_article)

    return articles


# ── Chunker ──────────────────────────────────────────────────────────────────

def split_by_khoan(lines: list[str]) -> dict[str, list[str]]:
    """
    Chia list dòng thành dict { "1": [...], "2": [...], ... }
    Dựa trên pattern khoản "1. ", "2. " ...
    """
    khoans = {}
    current_k = "intro"
    for line in lines:
        if RE_KHOAN.match(line):
            # Lấy số khoản
            num = line.split(".")[0].strip()
            current_k = num
            khoans.setdefault(current_k, []).append(line)
        else:
            khoans.setdefault(current_k, []).append(line)
    return khoans


def build_chunks(articles: list[dict]) -> list[dict]:
    """
    Từ list articles → list chunks với metadata đầy đủ.
    """
    chunks = []
    chunk_index = 0

    for art in articles:
        lines = art["raw_lines"]
        full_content = "\n".join(lines)
        header = f"Điều {art['article_num']}. {art['article_title']}"

        base_meta = {
            "source":        "01_VBHN-VPQH_363655_HinhSuHopNhat2017.docx",
            "doc_name":      "Bộ luật Hình sự (hợp nhất 2017)",
            "part":          art["part"],
            "chapter":       art["chapter"],
            "chapter_title": art["chapter_title"],
            "article_num":   art["article_num"],
            "article_title": art["article_title"],
        }

        # Nếu ngắn → 1 chunk "full"
        if len(full_content) <= MAX_CHARS:
            chunks.append({
                "id":          f"blhs_dieu_{art['article_num']}",
                "content":     f"{header}\n{full_content}",
                "metadata": {
                    **base_meta,
                    "chunk_type":   "full",
                    "khoan_num":    "",
                    "chunk_index":  chunk_index,
                    "total_chars":  len(full_content),
                }
            })
            chunk_index += 1

        # Nếu dài → split theo Khoản
        else:
            khoans = split_by_khoan(lines)
            for k_num, k_lines in khoans.items():
                k_text = "\n".join(k_lines)
                if not k_text.strip():
                    continue
                label = f"Khoản {k_num}" if k_num != "intro" else "Mở đầu"
                chunks.append({
                    "id":      f"blhs_dieu_{art['article_num']}_khoan_{k_num}",
                    "content": f"{header} – {label}\n{k_text}",
                    "metadata": {
                        **base_meta,
                        "chunk_type":  "khoan",
                        "khoan_num":   k_num,
                        "chunk_index": chunk_index,
                        "total_chars": len(k_text),
                    }
                })
                chunk_index += 1

    return chunks


# ── Ingest vào ChromaDB ──────────────────────────────────────────────────────

def ingest_to_chroma(chunks: list[dict]):
    from app.rag.retrieval import get_rag_system

    print(f"[3/4] Khởi tạo RAG system (load embedding model)...")
    t0 = time.time()
    rag = get_rag_system()
    print(f"      Xong sau {time.time()-t0:.1f}s")

    print(f"[4/4] Đang embed và lưu {len(chunks)} chunks vào ChromaDB...")
    t1 = time.time()

    # Gọi add_documents_batch để tận dụng code có sẵn
    docs = [{"content": c["content"], "metadata": c["metadata"]} for c in chunks]
    rag.add_documents_batch(docs)

    print(f"      Xong sau {time.time()-t1:.1f}s")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    default = os.path.join(
        os.path.dirname(__file__),
        "data", "01_VBHN-VPQH_363655_HinhSuHopNhat2017.docx"
    )
    file_path = sys.argv[1] if len(sys.argv) > 1 else default

    if not os.path.exists(file_path):
        print(f"[ERROR] Không tìm thấy: {file_path}")
        sys.exit(1)

    print(f"\n[1/4] Parse file: {os.path.basename(file_path)}")
    articles = parse_articles(file_path)
    print(f"      Tìm thấy {len(articles)} Điều")

    print(f"[2/4] Tạo chunks (MAX_CHARS={MAX_CHARS})...")
    chunks = build_chunks(articles)

    full_count  = sum(1 for c in chunks if c["metadata"]["chunk_type"] == "full")
    khoan_count = sum(1 for c in chunks if c["metadata"]["chunk_type"] == "khoan")
    print(f"      Tổng chunks : {len(chunks)}")
    print(f"      Chunk full  : {full_count}")
    print(f"      Chunk khoản : {khoan_count}")

    # Preview 3 chunks đầu
    print("\n── Preview 3 chunks đầu ──")
    for c in chunks[:3]:
        print(f"  ID      : {c['id']}")
        print(f"  Chương  : {c['metadata']['chapter']} – {c['metadata']['chapter_title']}")
        print(f"  Điều    : {c['metadata']['article_num']}. {c['metadata']['article_title']}")
        print(f"  Type    : {c['metadata']['chunk_type']}")
        print(f"  Chars   : {c['metadata']['total_chars']}")
        print(f"  Content : {c['content'][:120]}...")
        print()

    # Lưu preview JSON
    preview_path = os.path.join(os.path.dirname(file_path), "chunks_preview.json")
    with open(preview_path, "w", encoding="utf-8") as f:
        json.dump(chunks[:], f, ensure_ascii=False, indent=2)
    print(f"  Preview JSON: {preview_path}")

    # Hỏi trước khi ingest
    print("\nBạn có muốn ingest vào ChromaDB không? (y/n): ", end="", flush=True)
    ans = input().strip().lower()
    if ans == "y":
        ingest_to_chroma(chunks)
        print(f"\n[DONE] Đã index {len(chunks)} chunks vào ChromaDB.")
    else:
        print("Bỏ qua ingest. Chunks đã được preview ở file JSON.")


if __name__ == "__main__":
    main()
