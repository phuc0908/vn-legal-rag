"""
So sánh pure vector search vs hybrid search trên tập queries lớn.
Kết quả được cache → có thể dừng giữa chừng và chạy tiếp.

Workflow:
    1. Chuẩn bị file queries (một câu hỏi mỗi dòng):
           queries.txt

    2. Chạy collect (có thể dừng/tiếp bất cứ lúc nào):
           python scripts/eval_hybrid.py collect --queries queries.txt

    3. Xem báo cáo:
           python scripts/eval_hybrid.py report

    4. (Tuỳ chọn) Xem chi tiết 1 query:
           python scripts/eval_hybrid.py detail --query "Điều 8 luật hôn nhân"

Cache lưu tại: scripts/eval_cache/results.json
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
import json
import time
import hashlib
import argparse

sys.path.insert(0, BASE_DIR)

CACHE_DIR = os.path.join(_SCRIPTS_DIR, "eval_cache")
CACHE_FILE = os.path.join(CACHE_DIR, "results.json")
TOP_K = 5


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _qid(query: str) -> str:
    return hashlib.md5(query.strip().encode()).hexdigest()[:12]


def load_cache() -> dict:
    if not os.path.exists(CACHE_FILE):
        return {}
    with open(CACHE_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_cache(cache: dict):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    save_topic_map(cache)


def save_topic_map(cache: dict):
    """Lưu mapping query -> chủ đề ra file riêng để dễ kiểm tra độ chính xác của router."""
    mapping = []
    for data in cache.values():
        mapping.append({
            "query": data["query"],
            "chu_de_name": data.get("chu_de_name"),
            "chu_de_id": data.get("chu_de_id")
        })
    map_file = os.path.join(CACHE_DIR, "topic_mapping.json")
    with open(map_file, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)


def _trim_results(results: list) -> list:
    """Chỉ lưu những fields cần thiết để file cache không quá lớn."""
    trimmed = []
    for r in results:
        meta = r.get("metadata", {})
        trimmed.append({
            "content": r["content"],
            "score": round(float(r["score"]), 6),
            "dieu_mapc": meta.get("dieu_mapc", ""),
            "chu_de": meta.get("chu_de", ""),
            "de_muc": meta.get("de_muc", ""),
            "tieu_de": meta.get("tieu_de", "") or meta.get("dieu_ten", ""),
        })
    return trimmed


# ── Search helpers ────────────────────────────────────────────────────────────

# Topics cố định kèm đề mục con — lấy từ MySQL một lần
_HARDCODED_TOPICS = [
    {"id": "01684735-cbae-4b6f-9471-1010ab2f350a", "ten": "Tương trợ tư pháp", "demucs": ["Tương trợ tư pháp"]},
    {"id": "0672ce80-caa2-4d12-a474-6d86349c9dab", "ten": "Hình sự", "demucs": ["Hình sự"]},
    {"id": "09ca05d1-7f1d-4887-a65d-a210374d1969", "ten": "Thuế, phí, lệ phí, các khoản thu khác", "demucs": ["Quản lý thuế", "Thuế thu nhập doanh nghiệp", "Thuế thu nhập cá nhân", "Thuế giá trị gia tăng", "Thuế tiêu thụ đặc biệt", "Thuế xuất khẩu, thuế nhập khẩu", "Thuế bảo vệ môi trường", "Phí và lệ phí", "Chi phí tố tụng"]},
    {"id": "0f8741e9-b3d2-488b-aa70-961ccc802227", "ten": "Ngân hàng, tiền tệ", "demucs": ["Ngân hàng Nhà nước Việt Nam", "Các tổ chức tín dụng", "Bảo hiểm tiền gửi", "Ngoại hối", "Các công cụ chuyển nhượng", "Phòng, chống rửa tiền"]},
    {"id": "0fb2411e-095b-4095-bbbe-fb8465ec4199", "ten": "Giáo dục, đào tạo", "demucs": ["Giáo dục", "Giáo dục đại học"]},
    {"id": "11a7e159-46bf-48bf-93ec-4e415f84c678", "ten": "Xây dựng, nhà ở, đô thị", "demucs": ["Xây dựng", "Nhà ở", "Kinh doanh bất động sản", "Quy hoạch đô thị", "Kiến trúc"]},
    {"id": "1657cd3c-c513-4df5-ae6b-e39a778c640d", "ten": "Môi trường", "demucs": ["Bảo vệ môi trường", "Đa dạng sinh học"]},
    {"id": "1afcaf4b-85cb-4039-8627-3a8a101a7e5b", "ten": "Tài sản công, nợ công, dự trữ nhà nước", "demucs": ["Quản lý, sử dụng tài sản công", "Quản lý nợ công", "Dự trữ quốc gia", "Quản lý và sử dụng nguồn hỗ trợ phát triển chính thức (ODA)"]},
    {"id": "1c1f149f-f1bf-4ddb-9f6b-b2adbf17d410", "ten": "Văn thư lưu trữ", "demucs": ["Công tác văn thư", "Lưu trữ"]},
    {"id": "3a225bc6-c8c9-459e-967e-9876d4eb2c33", "ten": "Công nghiệp", "demucs": ["Dầu khí", "Điện lực", "Hóa chất", "Khuyến công", "Tiết kiệm năng lượng", "Khoáng sản"]},
    {"id": "3f0ce861-9980-43c9-9dcc-8e064c536bee", "ten": "Khoa học, công nghệ", "demucs": ["Khoa học và công nghệ", "Chuyển giao công nghệ", "Công nghệ cao", "Chất lượng sản phẩm, hàng hóa", "Đo lường", "Sở hữu trí tuệ", "Tiêu chuẩn và quy chuẩn kỹ thuật"]},
    {"id": "3fc1ee9d-eec6-4839-9c98-7ac2ca9e0792", "ten": "Tổ chức bộ máy nhà nước", "demucs": ["Bầu cử đại biểu Quốc hội và đại biểu Hội đồng nhân dân", "Hoạt động giám sát của Quốc hội và Hội đồng nhân dân", "Mặt trận Tổ quốc Việt Nam", "Thủ đô", "Tổ chức chính quyền địa phương"]},
    {"id": "487180ab-07c0-45c1-9e73-1ab76b2a55c9", "ten": "Văn hóa, thể thao, du lịch", "demucs": ["Di sản văn hóa", "Du lịch", "Thể dục, thể thao", "Điện ảnh", "Quảng cáo", "Hoạt động nghệ thuật biểu diễn"]},
    {"id": "48d084d9-d3f1-4c13-a898-dde6840fe0ff", "ten": "Tôn giáo, tín ngưỡng", "demucs": ["Tín ngưỡng, tôn giáo"]},
    {"id": "5576c952-dabe-4363-b94a-13419996ff4b", "ten": "Bảo hiểm", "demucs": ["Bảo hiểm xã hội", "Bảo hiểm y tế", "Kinh doanh bảo hiểm"]},
    {"id": "607817d9-0840-4986-b41f-5f3e9ae650c2", "ten": "Y tế, dược", "demucs": ["Dược", "Bảo vệ sức khỏe nhân dân", "An toàn thực phẩm", "Hiến, lấy, ghép mô, bộ phận cơ thể người", "Phòng, chống HIV/AIDS", "Phòng, chống bệnh truyền nhiễm"]},
    {"id": "6db952fa-b9dd-41f7-adf5-ccb22100ac9c", "ten": "Ngoại giao, điều ước quốc tế", "demucs": ["Điều ước quốc tế", "Cơ quan đại diện nước CHXHCN Việt Nam ở nước ngoài", "Hàm, cấp ngoại giao", "Người Việt Nam định cư ở nước ngoài"]},
    {"id": "717625a2-281b-4307-b21b-68b1c73d2207", "ten": "Thương mại, đầu tư, chứng khoán", "demucs": ["Đầu tư", "Thương mại", "Chứng khoán", "Đấu thầu", "Cạnh tranh", "Bảo vệ quyền lợi người tiêu dùng", "Quản lý ngoại thương", "Nhượng quyền thương mại"]},
    {"id": "73b6a37d-b55b-443d-b0fd-8f7d1b215ca1", "ten": "Thông tin, báo chí, xuất bản", "demucs": ["Báo chí", "Xuất bản", "Tiếp cận thông tin", "Hoạt động in"]},
    {"id": "7a9dcc15-370d-40b4-a02b-28e583b25dbf", "ten": "Tài chính", "demucs": ["Ngân sách nhà nước", "Hải quan", "Giá", "Thực hành tiết kiệm, chống lãng phí"]},
    {"id": "81215563-6346-448e-bded-2933f86276bb", "ten": "Nông nghiệp, nông thôn", "demucs": ["Lâm nghiệp", "Thủy sản", "Trồng trọt", "Chăn nuôi", "Bảo vệ và kiểm dịch thực vật", "Thú y", "Đê điều", "Thủy lợi"]},
    {"id": "8545ecbc-f0ce-44aa-83d6-c43d056f63f2", "ten": "Dân sự", "demucs": ["Dân sự", "Đăng ký biện pháp bảo đảm"]},
    {"id": "859b54fa-0c05-4807-a50c-c8be82fcae62", "ten": "Quốc phòng", "demucs": ["Quân nhân chuyên nghiệp", "Sĩ quan Quân đội nhân dân Việt Nam", "Nghĩa vụ quân sự", "Dân quân tự vệ", "Biên phòng Việt Nam", "Công nghiệp quốc phòng"]},
    {"id": "88a4972a-48c2-4def-926b-a71b9f6e4be7", "ten": "Thi hành án", "demucs": ["Thi hành án dân sự", "Thi hành án hình sự", "Đặc xá", "Thi hành tạm giữ, tạm giam"]},
    {"id": "8e485a16-50aa-4c80-9fbe-3b286287f8c1", "ten": "Doanh nghiệp, hợp tác xã", "demucs": ["Doanh nghiệp", "Hợp tác xã", "Hỗ trợ doanh nghiệp nhỏ và vừa", "Tổ hợp tác"]},
    {"id": "965fd0b7-e8b0-434a-83c2-9f9b2b4fbcba", "ten": "Trật tự, an toàn xã hội", "demucs": ["Cư trú", "Căn cước công dân", "Phòng cháy, chữa cháy", "Giao thông đường bộ (TTATXH)", "Phòng, chống ma túy", "Xử lý vi phạm hành chính"]},
    {"id": "9daf2b7f-cf24-4c97-adf8-0903f6b7f18e", "ten": "Kế toán, kiểm toán", "demucs": ["Kế toán", "Kiểm toán độc lập", "Kiểm toán Nhà nước"]},
    {"id": "a5b5fa2d-056c-48c4-b6fc-c782359511ff", "ten": "Hành chính tư pháp", "demucs": ["Hộ tịch", "Nuôi con nuôi", "Lý lịch tư pháp", "Quốc tịch", "Chứng thực"]},
    {"id": "a6ee2d1a-2edc-4c30-bff5-81efbd765464", "ten": "Dân tộc", "demucs": ["Công tác dân tộc"]},
    {"id": "b64f0e6a-3020-4c4a-be45-a1e5370a0939", "ten": "Đất đai", "demucs": ["Đất đai"]},
    {"id": "b82ee309-2527-4a7d-8d4d-fccdfabbc86c", "ten": "Giao thông, vận tải", "demucs": ["Giao thông đường bộ", "Đường sắt", "Hàng không dân dụng Việt Nam", "Hàng hải Việt Nam", "Giao thông đường thủy nội địa"]},
    {"id": "c054141c-d30c-4e83-9f35-2fb1c61c6e7c", "ten": "Tài nguyên", "demucs": ["Tài nguyên nước", "Địa chất và Khoáng sản", "Đo đạc và bản đồ", "Khí tượng thủy văn", "Tài nguyên, môi trường biển và hải đảo"]},
    {"id": "c124612e-a23f-4199-8747-55fe4e8a8c89", "ten": "Bưu chính, viễn thông", "demucs": ["Bưu chính", "Viễn thông", "Công nghệ thông tin", "Giao dịch điện tử", "An toàn thông tin mạng", "Tần số vô tuyến điện"]},
    {"id": "c3b69131-2931-4f67-926e-b244e18e8081", "ten": "An ninh quốc gia", "demucs": ["An ninh quốc gia", "Biên giới quốc gia", "Biển Việt Nam", "Bảo vệ bí mật nhà nước", "Cảnh sát biển Việt Nam"]},
    {"id": "c7ee2251-ddf9-4c7a-88f8-a9568fad0247", "ten": "Thi đua, khen thưởng, các danh hiệu vinh dự nhà nước", "demucs": ["Thi đua, khen thưởng"]},
    {"id": "cb5c6841-2c38-48ca-b946-da24c8d8a099", "ten": "Cán bộ, công chức, viên chức", "demucs": ["Cán bộ, công chức", "Viên chức", "Thẩm phán và Hội thẩm Tòa án nhân dân", "Kiểm sát viên Viện kiểm sát nhân dân"]},
    {"id": "ce9b9ff4-87dd-44d1-add8-27c1ec82d856", "ten": "Tổ chức chính trị - xã hội, hội", "demucs": ["Công đoàn", "Thanh niên", "Hoạt động chữ thập đỏ", "Quyền lập hội"]},
    {"id": "cef09501-9f71-4c9a-aa35-238ea8c79f76", "ten": "Tố tụng và các phương thức giải quyết tranh chấp", "demucs": ["Tố tụng dân sự", "Tố tụng hành chính", "Tố tụng hình sự", "Trọng tài thương mại", "Hòa giải", "Phá sản"]},
    {"id": "e4b6a170-8415-42a5-9ee2-f8eb147f5d15", "ten": "Chính sách xã hội", "demucs": ["Ưu đãi người có công với cách mạng", "Người khuyết tật", "Người cao tuổi", "Chính sách trợ giúp xã hội"]},
    {"id": "e967223c-d26a-4c7f-a8d9-420843bd5bf9", "ten": "Bổ trợ tư pháp", "demucs": ["Luật sư", "Công chứng", "Giám định tư pháp", "Đấu giá tài sản", "Trợ giúp pháp lý", "Hòa giải viên thương mại"]},
    {"id": "ec61c177-8f68-4a69-a42b-2257d599d907", "ten": "Xây dựng pháp luật và thi hành pháp luật", "demucs": ["Ban hành văn bản quy phạm pháp luật", "Kiểm soát thủ tục hành chính", "Phổ biến, giáo dục pháp luật"]},
    {"id": "ed53d710-e3ae-4741-abc7-0f5dd82dec24", "ten": "Lao động", "demucs": ["Lao động", "Việc làm", "An toàn, vệ sinh lao động", "Giáo dục nghề nghiệp", "Người lao động Việt Nam đi làm việc ở nước ngoài theo hợp đồng"]},
    {"id": "ee961e69-7a8d-4405-8fe6-ecdf7e44323f", "ten": "Thống kê", "demucs": ["Thống kê"]},
    {"id": "efbefb52-bf45-41df-aaf4-6a4e833f333e", "ten": "Dân số, gia đình, trẻ em, bình đẳng giới", "demucs": ["Hôn nhân và gia đình", "Trẻ em", "Bình đẳng giới", "Dân số", "Phòng, chống bạo lực gia đình"]},
    {"id": "ff58c8ec-ab1b-4fdd-b732-5f09f9fa09cd", "ten": "Khiếu nại, tố cáo", "demucs": ["Khiếu nại", "Tố cáo", "Thanh tra", "Phòng, chống tham nhũng", "Tiếp công dân"]},
]


def init_search(ollama_model: str = "qwen2.5:3b"):
    """Khởi tạo vector store, BM25 index, và topic router. Chỉ gọi 1 lần."""
    from app.rag.retrieval import ChromaVectorStore, BM25Index, HybridRetriever
    from app.core.config import settings

    print("[INIT] Đang tải ChromaVectorStore (embedding model)...")
    t0 = time.time()
    vs = ChromaVectorStore()
    print(f"[INIT] Vector store sẵn sàng ({time.time()-t0:.1f}s)")

    bm25 = BM25Index(settings.BM25_INDEX_PATH)
    loaded = bm25.load()
    if not loaded:
        print(f"[WARN] BM25 index chưa tồn tại tại '{settings.BM25_INDEX_PATH}'")
        print("[WARN] Chạy: python scripts/build_bm25_index.py trước")
        return vs, None, None

    retriever = HybridRetriever(vs, bm25)

    # Topic router — dùng Ollama (local) cho tất cả các cases
    topics = _HARDCODED_TOPICS
    topic_map    = {str(t["id"]): t["ten"] for t in topics}
    idx_to_uuid  = {str(i): str(t["id"]) for i, t in enumerate(topics, 1)}
    topic_list_str = "\n".join(
        f"  {i}: {t['ten']}" + (f" [{', '.join(t['demucs'][:3])}]" if t.get('demucs') else "")
        for i, t in enumerate(topics, 1)
    )

    topic_router = None
    try:
        topic_router = OllamaRouter(topic_map, idx_to_uuid, topic_list_str, model=ollama_model)
        print(f"[INIT] OllamaRouter sẵn sàng (model={ollama_model}, {len(topics)} chủ đề)")
    except Exception as e:
        print(f"[WARN] TopicRouter không khởi tạo được: {e}")

    return vs, retriever, topic_router


# ── Ollama local router ───────────────────────────────────────────────────────

class OllamaRouter:
    """Dùng Ollama local để phân loại chủ đề — không rate limit."""

    def __init__(self, topic_map: dict, idx_to_uuid: dict, topic_list_str: str,
                 model: str = "qwen2.5:3b", base_url: str = "http://localhost:11434"):
        self._topic_map = topic_map
        self._idx_to_uuid = idx_to_uuid
        self._topic_list_str = topic_list_str
        self.model = model
        self.base_url = base_url
        self.llm = self  # Tương thích với _route_with_retry

    def _call(self, prompt: str, **kwargs) -> str:
        """Thực hiện gọi API Ollama với retry khi 500."""
        import requests as _req
        for attempt in range(4):
            try:
                resp = _req.post(
                    f"{self.base_url}/api/generate",
                    json={"model": self.model, "prompt": prompt, "stream": False},
                    timeout=180,
                )
                if resp.status_code == 500:
                    wait = 10 * (attempt + 1)
                    print(f"  [OLLAMA] 500 error, chờ {wait}s rồi retry ({attempt+1}/4)...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json().get("response", "").strip()
            except _req.exceptions.Timeout:
                wait = 15 * (attempt + 1)
                print(f"  [OLLAMA] Timeout, chờ {wait}s rồi retry ({attempt+1}/4)...")
                time.sleep(wait)
        raise RuntimeError("Ollama không phản hồi sau 4 lần thử")

    def route(self, query: str):
        import re as _re
        prompt = (
            f"Classify the Vietnamese legal question into ONE topic number.\n"
            f"Topics (subtopics in brackets help you choose correctly):\n"
            f"{self._topic_list_str}\n\n"
            f"Question: {query}\n\n"
            f"Reply with ONLY a single number (0 if none match):"
        )
        try:
            raw = self._call(prompt)
            match = _re.search(r"\d+", raw)
            if not match:
                return None
            idx = match.group(0)
            if idx == "0":
                return None
            uuid = self._idx_to_uuid.get(idx)
            if uuid and uuid in self._topic_map:
                print(f"  [OLLAMA] → {idx} = {self._topic_map[uuid]}")
                return uuid
        except Exception as e:
            print(f"  [OLLAMA] Lỗi: {e}")
        return None


# ── Query rewriter ───────────────────────────────────────────────────────────

_REWRITE_PROMPT = """Rewrite the Vietnamese legal question into an optimized search query for legal retrieval.

Rules:
- Keep any article numbers (Điều X) unchanged
- Add related legal terms and synonyms used in Vietnamese law
- Infer legal intent (e.g., "quyền lợi" → "nghĩa vụ của người sử dụng lao động", "bồi thường", "trợ cấp")
- Keep it concise (1 sentence)
- Prioritize terms that appear in legal documents
- Output ONLY the rewritten query in Vietnamese

Question: {query}

Rewritten query:"""


def _rewrite_query(ollama_router, query: str) -> str:
    """Dùng Ollama rewrite query sang thuật ngữ pháp lý. Trả về query gốc nếu lỗi."""
    import re as _re
    try:
        prompt = _REWRITE_PROMPT.format(query=query)
        rewritten = ollama_router._call(prompt)
        rewritten = rewritten.strip().splitlines()[0].strip()
        # Bỏ prefix thừa
        rewritten = _re.sub(r'^(Rewritten query|Truy vấn pháp lý|Truy vấn|Query)\s*:\s*', '', rewritten, flags=_re.IGNORECASE)
        rewritten = rewritten.strip().strip('"').strip("'")
        # Bỏ nếu có chữ Hán hoặc quá ngắn
        has_cjk = bool(_re.search(r'[\u4e00-\u9fff]', rewritten))
        if has_cjk or len(rewritten) < 5:
            print(f"  [REWRITE] Kết quả không hợp lệ ({rewritten[:50]}), dùng query gốc")
            return query
        print(f"  [REWRITE] {rewritten[:100]}")
        return rewritten
    except Exception as e:
        print(f"  [REWRITE] Lỗi: {e}")
        return query


# ── Keyword-based router (fast override trước khi gọi LLM) ───────────────────

_KEYWORD_RULES = [
    (["hình sự", "bộ luật hình sự", "blhs", "tội phạm", "hình phạt", "phạt tù",
      "truy tố", "khởi tố", "bị can", "bị cáo"],
     "0672ce80-caa2-4d12-a474-6d86349c9dab"),
    (["lao động", "bộ luật lao động", "hợp đồng lao động", "người lao động",
      "sa thải", "thôi việc", "tiền lương", "lương tối thiểu", "đình công"],
     "ed53d710-e3ae-4741-abc7-0f5dd82dec24"),
    (["hôn nhân", "luật hôn nhân", "ly hôn", "kết hôn", "vợ chồng", "cấp dưỡng"],
     "efbefb52-bf45-41df-aaf4-6a4e833f333e"),
    (["bộ luật dân sự", "blds", "thừa kế", "di chúc"],
     "8545ecbc-f0ce-44aa-83d6-c43d056f63f2"),
    (["doanh nghiệp", "luật doanh nghiệp", "công ty", "cổ đông", "vốn điều lệ", "hợp tác xã"],
     "8e485a16-50aa-4c80-9fbe-3b286287f8c1"),
    (["đất đai", "luật đất đai", "quyền sử dụng đất", "sổ đỏ", "sổ hồng",
      "thu hồi đất", "chuyển nhượng đất"],
     "b64f0e6a-3020-4c4a-be45-a1e5370a0939"),
    (["nhà ở", "luật nhà ở", "bất động sản", "mua bán nhà", "chung cư",
      "luật xây dựng", "giấy phép xây dựng"],
     "11a7e159-46bf-48bf-93ec-4e415f84c678"),
    (["tai nạn giao thông", "vi phạm giao thông", "giấy phép lái xe", "luật giao thông"],
     "b82ee309-2527-4a7d-8d4d-fccdfabbc86c"),
    (["thuế thu nhập", "thuế giá trị gia tăng", "hoàn thuế", "khai thuế", "quản lý thuế"],
     "09ca05d1-7f1d-4887-a65d-a210374d1969"),
    (["bảo hiểm xã hội", "bhxh", "bảo hiểm y tế", "bhyt", "bảo hiểm thất nghiệp", "lương hưu"],
     "5576c952-dabe-4363-b94a-13419996ff4b"),
    (["khiếu nại", "tố cáo", "thanh tra", "tham nhũng", "xử phạt hành chính"],
     "ff58c8ec-ab1b-4fdd-b732-5f09f9fa09cd"),
    (["thi hành án", "chấp hành án", "tạm giam", "tạm giữ"],
     "88a4972a-48c2-4def-926b-a71b9f6e4be7"),
    (["nghĩa vụ quân sự", "quân nhân", "biên phòng", "luật quốc phòng"],
     "859b54fa-0c05-4807-a50c-c8be82fcae62"),
    (["bệnh viện", "khám bệnh", "chữa bệnh", "dược phẩm", "an toàn thực phẩm"],
     "607817d9-0840-4986-b41f-5f3e9ae650c2"),
    (["luật giáo dục", "trường đại học", "tuyển sinh", "học phí"],
     "0fb2411e-095b-4095-bbbe-fb8465ec4199"),
    (["ngân hàng", "tín dụng", "vay vốn", "lãi suất", "thế chấp"],
     "0f8741e9-b3d2-488b-aa70-961ccc802227"),
    (["bảo vệ môi trường", "ô nhiễm môi trường", "chất thải"],
     "1657cd3c-c513-4df5-ae6b-e39a778c640d"),
]


def _keyword_route(query: str, topic_map: dict):
    """Phân loại nhanh bằng từ khóa. Trả về UUID hoặc None."""
    q_lower = query.lower()
    for keywords, uuid in _KEYWORD_RULES:
        if any(kw in q_lower for kw in keywords):
            if uuid in topic_map:
                return uuid
    return None


# ── Router với retry ─────────────────────────────────────────────────────────

def _route_with_retry(topic_router, query: str):
    """
    Hàm wrapper gọi router và xử lý retry đơn giản cho Ollama.
    """
    import re as _re
    from app.rag.llm import TOPIC_ROUTER_PROMPT
    prompt_text = TOPIC_ROUTER_PROMPT.format(
        topic_list=topic_router._topic_list_str,
        question=query,
    )

    for attempt in range(3):
        try:
            raw = topic_router.llm._call(prompt_text, temperature=0.0, max_tokens=10)
            match = _re.search(r"\d+", raw.strip())
            if not match:
                return None
            idx = match.group(0)
            if idx == "0":
                return None
            # Ánh xạ từ số thứ tự sang UUID
            uuid = topic_router._idx_to_uuid.get(idx)
            if uuid and uuid in topic_router._topic_map:
                return uuid
            return None
        except Exception as e:
            print(f"  [ROUTER] Lỗi (lần {attempt+1}/3): {e}")
            if attempt < 2:
                time.sleep(2)
    return None


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_collect(queries_file: str, force: bool = False, no_router: bool = False,
                ollama_model: str = "qwen2.5:3b", no_rewrite: bool = False):
    """
    Chạy search cho từng query và lưu cache.
    Bỏ qua các query đã có trong cache (trừ khi --force).
    """
    if not os.path.exists(queries_file):
        print(f"[ERROR] Không tìm thấy file: {queries_file}")
        sys.exit(1)

    with open(queries_file, encoding="utf-8") as f:
        queries = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    print(f"[INFO] Tổng số queries: {len(queries)}")

    cache = load_cache()
    # Cần chạy nếu: force, chưa có cache, hoặc rewrite_skipped mà lần này có rewrite
    def _needs_run(q):
        if force:
            return True
        qid = _qid(q)
        if qid not in cache:
            return True
        if not no_rewrite and cache[qid].get("rewrite_skipped"):
            return True
        return False

    pending = [q for q in queries if _needs_run(q)]
    print(f"[INFO] Đã có trong cache: {len(queries) - len(pending)} | Cần chạy: {len(pending)}")

    if not pending:
        print("[INFO] Tất cả đã có cache. Dùng --force để chạy lại.")
        return

    vs, retriever, topic_router = init_search(ollama_model=ollama_model)
    if retriever is None:
        print("[ERROR] Không thể khởi tạo HybridRetriever. Build BM25 index trước.")
        sys.exit(1)
    if no_router:
        topic_router = None
        print("[INFO] --no-router: bỏ qua topic routing, chỉ chạy cases ① và ②")

    t_start = time.time()
    for i, query in enumerate(pending, 1):
        qid = _qid(query)
        print(f"\n[{i}/{len(pending)}] {query[:80]}")

        # ── Topic routing: keyword trước, LLM fallback ───────────────────────
        chu_de_id = None
        chu_de_name = None
        t_route = 0
        if topic_router:
            # Bước 1: keyword matching (< 1ms)
            t0 = time.time()
            chu_de_id = _keyword_route(query, topic_router._topic_map)
            t_route = time.time() - t0
            if chu_de_id:
                print(f"  [ROUTER] keyword match → {topic_router._topic_map.get(chu_de_id)} | {t_route*1000:.0f}ms")
            else:
                # Bước 2: LLM fallback
                for attempt in range(5):
                    t0 = time.time()
                    try:
                        chu_de_id = _route_with_retry(topic_router, query)
                    except Exception:
                        chu_de_id = None
                    t_route = time.time() - t0
                    if chu_de_id is not None:
                        break
                    if attempt < 4:
                        wait = 15 * (attempt + 1)
                        print(f"  [ROUTER] Retry {attempt+1}/4 sau {wait}s...")
                    time.sleep(wait)
            if chu_de_id:
                chu_de_name = topic_router._topic_map.get(str(chu_de_id))
            print(f"  [ROUTER] chu_de_id={chu_de_id} ({chu_de_name}) | {t_route*1000:.0f}ms")

        # ── Filter theo chu_de_id (ChromaDB yêu cầu string UUID sạch) ────────
        clean_chu_de_id = str(chu_de_id).strip() if chu_de_id else None
        filter_where = {"chu_de_id": clean_chu_de_id} if clean_chu_de_id else None
        
        if filter_where:
             print(f"  [COLLECT] Applying filter: {filter_where}")

        # ── Kiểm tra có đang "fill-in rewrite" cho entry đã có baseline không ──
        existing = cache.get(qid, {})
        filling_rewrite_only = (not no_rewrite and existing.get("rewrite_skipped"))

        # ── BM25 fetch (dùng chung cho tất cả cases) ─────────────────────────
        bm25_all = retriever.bm25_index.search(query, top_k=TOP_K * 10)
        bm25_filtered = [
            r for r in bm25_all
            if r.get("metadata", {}).get("chu_de_id") == clean_chu_de_id
        ] if clean_chu_de_id else []

        # ── Case 1 & 2: Vector + filter / Hybrid + filter ────────────────────
        vec_f, hyb_f = None, None
        t_vec_f = t_hyb_f = 0

        if filling_rewrite_only:
            # Tái dùng baseline từ cache, không cần tính lại
            vec_f  = existing.get("vec_f")
            hyb_f  = existing.get("hyb_f")
            t_vec_f = existing.get("t_vec_f_ms", 0) / 1000
            t_hyb_f = existing.get("t_hyb_f_ms", 0) / 1000
            print(f"  [FILL-RW] Tái dùng baseline từ cache (vec_f={len(vec_f or [])} docs)")
        elif filter_where:
            t0 = time.time()
            vec_f = vs.similarity_search(query, k=TOP_K, filter_where=filter_where)
            t_vec_f = time.time() - t0
            print(f"  [VEC_F]   scores: {[round(r['score'],4) for r in vec_f]}")

            t0 = time.time()
            hyb_f = retriever._rrf_fusion(vec_f, bm25_filtered, TOP_K)
            t_hyb_f = t_vec_f + (time.time() - t0)
            print(f"  [BM25_F]  {len(bm25_filtered)}/{len(bm25_all)} kept | [HYB_F] rrf: {[round(r['score'],5) for r in hyb_f]}")

        # ── Query rewrite (chỉ khi có filter và không bị tắt) ───────────────
        vec_rw, hyb_rw = None, None
        t_vec_rw = t_hyb_rw = 0
        rewritten_query = query

        if no_rewrite:
            print(f"  [REWRITE] Tắt (--no-rewrite)")
        elif filter_where:
            if topic_router and clean_chu_de_id:
                time.sleep(2)
                rewritten_query = _rewrite_query(topic_router, query)
            # ── Case 3: Vector + filter + rewrite ────────────────────────────
            bm25_rw_all = retriever.bm25_index.search(rewritten_query, top_k=TOP_K * 10)
            bm25_rw_filtered = [
                r for r in bm25_rw_all
                if r.get("metadata", {}).get("chu_de_id") == clean_chu_de_id
            ] if clean_chu_de_id else []

            t0 = time.time()
            vec_rw = vs.similarity_search(rewritten_query, k=TOP_K, filter_where=filter_where)
            t_vec_rw = time.time() - t0
            print(f"  [VEC_RW]  scores: {[round(r['score'],4) for r in vec_rw]}")

            t0 = time.time()
            hyb_rw = retriever._rrf_fusion(vec_rw, bm25_rw_filtered, TOP_K)
            t_hyb_rw = t_vec_rw + (time.time() - t0)
            print(f"  [HYB_RW]  rrf: {[round(r['score'],5) for r in hyb_rw]}")

        cache[qid] = {
            "query":          query,
            "rewritten_query": rewritten_query,
            "rewrite_skipped": no_rewrite,
            "chu_de_id":      chu_de_id,
            "chu_de_name":    chu_de_name,
            # Case 1: Vector + filter
            "vec_f":          _trim_results(vec_f) if vec_f is not None else None,
            "t_vec_f_ms":     round(t_vec_f * 1000),
            # Case 2: Hybrid + filter
            "hyb_f":          _trim_results(hyb_f) if hyb_f is not None else None,
            "t_hyb_f_ms":     round(t_hyb_f * 1000),
            # Case 3: Vector + filter + rewrite
            "vec_rw":         _trim_results(vec_rw) if vec_rw is not None else None,
            "t_vec_rw_ms":    round(t_vec_rw * 1000),
            # Case 4: Hybrid + filter + rewrite
            "hyb_rw":         _trim_results(hyb_rw) if hyb_rw is not None else None,
            "t_hyb_rw_ms":    round(t_hyb_rw * 1000),
        }

        save_cache(cache)

        elapsed = time.time() - t_start
        eta = elapsed / i * (len(pending) - i)
        print(f"  ETA={eta:.0f}s")

    print(f"\n[DONE] Hoàn tất {len(pending)} queries. Cache: {CACHE_FILE}")


def cmd_report():
    """In báo cáo tổng hợp từ cache."""
    cache = load_cache()
    if not cache:
        print("[ERROR] Cache trống. Chạy 'collect' trước.")
        return

    entries = list(cache.values())
    total = len(entries)

    # ── Thống kê overlap ──────────────────────────────────────────────────────
    overlap_counts = []         # số docs xuất hiện trong cả 2
    bm25_unique_counts = []     # số docs hybrid có mà vector không có
    vector_unique_counts = []   # số docs vector có mà hybrid không có
    rank_changes = []           # thay đổi rank trung bình của docs chung

    for e in entries:
        vec_ids  = [r["dieu_mapc"] for r in e["vector"]]
        hyb_ids  = [r["dieu_mapc"] for r in e["hybrid"]]

        overlap = set(vec_ids) & set(hyb_ids)
        overlap_counts.append(len(overlap))
        bm25_unique_counts.append(len(set(hyb_ids) - set(vec_ids)))
        vector_unique_counts.append(len(set(vec_ids) - set(hyb_ids)))

        # rank thay đổi cho docs chung
        for doc_id in overlap:
            rank_v = vec_ids.index(doc_id) + 1
            rank_h = hyb_ids.index(doc_id) + 1
            rank_changes.append(rank_v - rank_h)  # dương = hybrid rank cao hơn

    avg_overlap     = sum(overlap_counts) / total
    avg_bm25_unique = sum(bm25_unique_counts) / total
    avg_vec_unique  = sum(vector_unique_counts) / total
    avg_rank_change = sum(rank_changes) / len(rank_changes) if rank_changes else 0

    # ── Thống kê tốc độ ──────────────────────────────────────────────────────
    avg_t_vec = sum(e["t_vector_ms"] for e in entries) / total
    avg_t_hyb = sum(e["t_hybrid_ms"] for e in entries) / total

    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  BÁO CÁO: Vector vs Hybrid Search ({total} queries)")
    print(f"{sep}")

    print(f"\n--- Độ phủ kết quả (trung bình mỗi query, top-{TOP_K}) ---")
    print(f"  Docs chung (overlap)      : {avg_overlap:.1f}/{TOP_K}")
    print(f"  Docs mới từ BM25          : {avg_bm25_unique:.1f}  ← hybrid tìm thêm được")
    print(f"  Docs vector bị đẩy xuống  : {avg_vec_unique:.1f}")
    print(f"  Rank thay đổi trung bình  : {avg_rank_change:+.2f}  (+ = hybrid đẩy lên cao hơn)")

    print(f"\n--- Tốc độ (trung bình) ---")
    print(f"  Pure vector : {avg_t_vec:.0f}ms")
    print(f"  Hybrid      : {avg_t_hyb:.0f}ms  (+{avg_t_hyb-avg_t_vec:.0f}ms overhead BM25)")

    # ── Top queries hybrid khác vector nhiều nhất ─────────────────────────────
    print(f"\n--- Top 10 queries hybrid thay đổi nhiều nhất ---")
    diffs = []
    for e in entries:
        vec_ids = {r["dieu_mapc"] for r in e["vector"]}
        hyb_ids = {r["dieu_mapc"] for r in e["hybrid"]}
        diff = len(vec_ids.symmetric_difference(hyb_ids))
        diffs.append((diff, e["query"]))
    diffs.sort(reverse=True)
    for diff, q in diffs[:10]:
        print(f"  [{diff} docs khác] {q[:70]}")

    print(f"\n{sep}")
    print(f"  Chi tiết từng query: python scripts/eval_hybrid.py detail --query \"...\"")
    print(f"  File cache: {CACHE_FILE}")
    print(f"{sep}\n")


def cmd_detail(query: str):
    """In kết quả chi tiết cho 1 query."""
    cache = load_cache()
    qid = _qid(query)

    # Tìm gần đúng nếu không match chính xác
    entry = cache.get(qid)
    if not entry:
        matches = [e for e in cache.values() if query.lower() in e["query"].lower()]
        if not matches:
            print(f"[ERROR] Không tìm thấy '{query}' trong cache.")
            print("[INFO]  Chạy 'collect' trước hoặc kiểm tra lại query.")
            return
        entry = matches[0]

    sep = "-" * 60
    print(f"\n{'='*60}")
    print(f"  QUERY: {entry['query']}")
    print(f"{'='*60}")

    vec_ids = [r["dieu_mapc"] for r in entry["vector"]]
    hyb_ids = [r["dieu_mapc"] for r in entry["hybrid"]]

    print(f"\n[VECTOR ONLY]  ({entry['t_vector_ms']}ms)")
    for i, r in enumerate(entry["vector"], 1):
        marker = "  "
        if r["dieu_mapc"] not in hyb_ids:
            marker = "✗ "  # bị hybrid loại
        print(f"  {marker}{i}. [{r['dieu_mapc']}] score={r['score']:.4f}")
        if r["tieu_de"]:
            print(f"       {r['tieu_de'][:80]}")
        print(f"       {r['content'][:100].replace(chr(10), ' ')}...")

    print(f"\n[HYBRID: BM25 + Vector + RRF]  ({entry['t_hybrid_ms']}ms)")
    for i, r in enumerate(entry["hybrid"], 1):
        marker = "  "
        if r["dieu_mapc"] not in vec_ids:
            marker = "★ "  # mới từ BM25
        print(f"  {marker}{i}. [{r['dieu_mapc']}] rrf={r['score']:.5f}")
        if r["tieu_de"]:
            print(f"       {r['tieu_de'][:80]}")
        print(f"       {r['content'][:100].replace(chr(10), ' ')}...")

    new_docs = set(hyb_ids) - set(vec_ids)
    dropped  = set(vec_ids) - set(hyb_ids)
    print(f"\n  ★ Docs mới từ BM25: {len(new_docs)} — {new_docs if new_docs else '(không có)'}")
    print(f"  ✗ Docs bị loại bỏ: {len(dropped)} — {dropped if dropped else '(không có)'}")


# ── HTML Report ───────────────────────────────────────────────────────────────

def cmd_html(out_path: str = None):
    """Xuất báo cáo HTML so sánh vector vs hybrid."""
    cache = load_cache()
    if not cache:
        print("[ERROR] Cache trống. Chạy 'collect' trước.")
        return

    out_path = out_path or os.path.join(CACHE_DIR, "report.html")
    entries  = list(cache.values())
    total    = len(entries)

    # ── Tính stats ────────────────────────────────────────────────────────────
    rows_data = []
    n_has_new = 0
    for e in entries:
        vec_f_data = e.get("vec_f") or []
        hyb_f_data = e.get("hyb_f") or []
        vec_ids = [r["dieu_mapc"] for r in vec_f_data]
        hyb_ids = [r["dieu_mapc"] for r in hyb_f_data]
        new_docs     = set(hyb_ids) - set(vec_ids)
        dropped_docs = set(vec_ids) - set(hyb_ids)
        top1_changed = vec_ids[:1] != hyb_ids[:1]
        if new_docs:
            n_has_new += 1
        rows_data.append({
            "entry": e,
            "vec_ids": vec_ids,
            "hyb_ids": hyb_ids,
            "new_docs": new_docs,
            "dropped_docs": dropped_docs,
            "top1_changed": top1_changed,
        })

    avg_t_vec = sum(e.get("t_vec_f_ms", 0) for e in entries) / total
    avg_t_hyb = sum(e.get("t_hyb_f_ms", 0) for e in entries) / total

    # ── Helpers render ────────────────────────────────────────────────────────
    def esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def to_html(s: str) -> str:
        """Strip HTML tags, format cấu trúc pháp lý: khoản 1/2/3, điểm a/b/c."""
        import re
        # Strip HTML tags gốc
        s = re.sub(r'<[^>]+>', ' ', s)
        s = re.sub(r'[ \t]+', ' ', s).strip()

        # Chèn newline trước các marker cấu trúc pháp lý (kể cả khi không có \n)
        # Khoản: "1. ", "2. ", "10. " — số + chấm + khoảng trắng
        s = re.sub(r'\s+(\d{1,2})\.\s+(?=[A-ZĐÁĂÂÉÊÍÓÔƠÚƯÀẢÃẠĂẮẶÂẦẤẨẪẬÈẺẼẸÊỀẾỂỄỆÌỈĨỊÒỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙỦŨỤƯỪỨỬỮỰỲỶỸỴ])',
                   r'\n\1. ', s)
        # Điểm: "a) ", "b) ", "đ) "
        s = re.sub(r'\s+([a-zđ])\)\s+', r'\n\1) ', s)

        lines = s.split('\n')
        out = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            e = esc(line)
            # Header metadata (Chủ đề | Đề mục | Chương)
            if '|' in line and any(k in line for k in ('Chủ đề', 'Đề mục', 'Chương', 'Điều:')):
                out.append(f'<div class="header-meta">{e}</div>')
            # Tên điều
            elif re.match(r'^Điều\s+\S+\.?\s', line) or re.match(r'^(Chương|Mục|Phần)\s', line):
                out.append(f'<div class="ten-dieu">{e}</div>')
            # Khoản: bắt đầu bằng số + chấm
            elif re.match(r'^\d{1,2}\.', line):
                out.append(f'<div class="khoan">{e}</div>')
            # Điểm: bắt đầu bằng chữ thường + dấu ngoặc
            elif re.match(r'^[a-zđ]\)', line):
                out.append(f'<div class="diem">{e}</div>')
            else:
                out.append(f'<div class="normal-line">{e}</div>')
        return '\n'.join(out)

    def rank_arrow(vec_rank, hyb_rank):
        """Tạo badge hiển thị thay đổi rank: '#3→#1', 'BM25→#2'."""
        if vec_rank is None:
            return f'<span class="rank-arrow rank-up">BM25→#{hyb_rank}</span>'
        diff = vec_rank - hyb_rank
        if diff > 0:
            return f'<span class="rank-arrow rank-up">#{vec_rank}→#{hyb_rank} ▲{diff}</span>'
        elif diff < 0:
            return f'<span class="rank-arrow rank-down">#{vec_rank}→#{hyb_rank} ▼{abs(diff)}</span>'
        else:
            return f'<span class="rank-arrow rank-same">#{vec_rank}→#{hyb_rank}</span>'

    def render_doc_row(r, label_class, rank, badge=""):
        tieu_de = esc(r.get("tieu_de") or "")
        chu_de  = esc(r.get("chu_de") or "")
        de_muc  = esc(r.get("de_muc") or "")
        content = to_html(r["content"])
        score   = r["score"]
        return f"""
        <tr class="{label_class}">
          <td class="rank">{rank}</td>
          <td class="text">
            <div class="meta-row">
              {f'<span class="chu-de">{chu_de}</span>' if chu_de else ''}
              {f'<span class="de-muc">{de_muc}</span>' if de_muc else ''}
              {badge}
              <span class="score-inline">{score:.5f}</span>
            </div>
            {f'<div class="tieu-de">{tieu_de}</div>' if tieu_de else ''}
            <div class="noidung">{content}</div>
          </td>
        </tr>"""

    def build_col_rows(source_list, compare_list):
        """Render rows cho 1 cột, so rank với cột compare_list."""
        compare_map = {r["dieu_mapc"]: i for i, r in enumerate(compare_list, 1)} if compare_list else {}
        rows = ""
        for i, r in enumerate(source_list, 1):
            mapc = r["dieu_mapc"]
            cmp_pos = compare_map.get(mapc)
            if cmp_pos is None and compare_list is not None:
                badge = '<span class="badge dropped-badge">bị loại</span>'
                cls = "dropped"
            elif cmp_pos is None:
                badge = ""
                cls = ""
            elif cmp_pos < i:
                badge = rank_arrow(i, cmp_pos)
                cls = "rank-improved"
            elif cmp_pos > i:
                badge = rank_arrow(i, cmp_pos)
                cls = "rank-fell"
            else:
                badge = rank_arrow(i, cmp_pos)
                cls = ""
            rows += render_doc_row(r, cls, i, badge)
        return rows

    def build_hyb_rows(hyb_list, vec_list):
        """Render hybrid rows — badge ★BM25 nếu doc không có trong vec_list."""
        vec_map = {r["dieu_mapc"]: i for i, r in enumerate(vec_list, 1)} if vec_list else {}
        rows = ""
        for i, r in enumerate(hyb_list, 1):
            mapc = r["dieu_mapc"]
            vec_pos = vec_map.get(mapc)
            if vec_pos is None:
                badge = rank_arrow(None, i)
                cls = "newdoc"
            elif vec_pos > i:
                badge = rank_arrow(vec_pos, i)
                cls = "rank-improved"
            elif vec_pos < i:
                badge = rank_arrow(vec_pos, i)
                cls = "rank-fell"
            else:
                badge = rank_arrow(vec_pos, i)
                cls = ""
            rows += render_doc_row(r, cls, i, badge)
        return rows

    def _na_cell(msg):
        return f"<tr><td colspan=2 class='na'>{msg}</td></tr>"

    def _col_or_na(data, compare, build_fn, no_router_msg="router không xác định chủ đề", skipped=False):
        if skipped:
            return _na_cell("Rewrite bị tắt (--no-rewrite) — chạy lại không có flag này để so sánh")
        if data is None:
            return _na_cell(f"Không có filter ({no_router_msg})")
        if len(data) == 0:
            return _na_cell("0 kết quả (chủ đề chưa có trong ChromaDB)")
        return build_fn(data, compare)

    def render_entry(d):
        e   = d["entry"]
        q   = esc(e["query"])
        rw  = esc(e.get("rewritten_query") or "")
        chu_de_name = esc(e.get("chu_de_name") or "")

        changed_badge = '<span class="badge changed">TOP-1 ĐỔI</span>' if d["top1_changed"] else ""
        new_badge     = f'<span class="badge new">+{len(d["new_docs"])} docs mới</span>' if d["new_docs"] else ""
        filter_badge  = (f'<span class="badge filter-badge">{chu_de_name}</span>'
                         if chu_de_name else '<span class="badge no-filter">router: không rõ chủ đề</span>')
        rw_block = (f'<div class="rewritten-query">Rewrite: <em>{rw}</em></div>' if rw and rw != q else "")

        vec_f  = e.get("vec_f")
        hyb_f  = e.get("hyb_f")
        vec_rw = e.get("vec_rw")
        hyb_rw = e.get("hyb_rw")

        rw_skipped = e.get("rewrite_skipped", False)
        col1 = _col_or_na(vec_f,  hyb_f,  build_col_rows)
        col2 = _col_or_na(hyb_f,  vec_f,  build_hyb_rows)
        col3 = _col_or_na(vec_rw, hyb_rw, build_col_rows, skipped=rw_skipped)
        col4 = _col_or_na(hyb_rw, vec_rw, build_hyb_rows, skipped=rw_skipped)

        t1 = e.get('t_vec_f_ms', 0)
        t2 = e.get('t_hyb_f_ms', 0)
        t3 = e.get('t_vec_rw_ms', 0)
        t4 = e.get('t_hyb_rw_ms', 0)

        return f"""
    <div class="query-block {'has-diff' if d['new_docs'] or d['top1_changed'] else ''}">
      <div class="query-header">
        <span class="query-text">{q}</span>
        {changed_badge}{new_badge}{filter_badge}
      </div>
      {rw_block}
      <div class="section-label filtered">Filter: {chu_de_name or '—'} | Query gốc</div>
      <div class="tables">
        <div class="half">
          <div class="table-label">① Vector + filter <span class="t-ms">{t1}ms</span></div>
          <table><thead><tr><th>#</th><th>Nội dung điều luật</th></tr></thead>
          <tbody>{col1}</tbody></table>
        </div>
        <div class="half">
          <div class="table-label">② Hybrid + filter <span class="t-ms">{t2}ms</span></div>
          <table><thead><tr><th>#</th><th>Nội dung điều luật</th></tr></thead>
          <tbody>{col2}</tbody></table>
        </div>
      </div>
      <div class="section-label rewrite">Filter: {chu_de_name or '—'} | Query rewrite</div>
      <div class="tables">
        <div class="half">
          <div class="table-label">③ Vector + filter + rewrite <span class="t-ms">{t3}ms</span></div>
          <table><thead><tr><th>#</th><th>Nội dung điều luật</th></tr></thead>
          <tbody>{col3}</tbody></table>
        </div>
        <div class="half">
          <div class="table-label">④ Hybrid + filter + rewrite <span class="t-ms">{t4}ms</span></div>
          <table><thead><tr><th>#</th><th>Nội dung điều luật</th></tr></thead>
          <tbody>{col4}</tbody></table>
        </div>
      </div>
    </div>"""

    entries_html = "\n".join(render_entry(d) for d in rows_data)

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>Hybrid Search Eval Report</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f5f5f5; margin: 0; padding: 20px; color: #333; }}
  h1   {{ color: #2c3e50; margin-bottom: 4px; }}
  .summary {{ background: #fff; border-radius: 8px; padding: 16px 24px;
              margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.1);
              display: flex; gap: 40px; flex-wrap: wrap; }}
  .stat {{ text-align: center; }}
  .stat .val {{ font-size: 2em; font-weight: 700; color: #2980b9; }}
  .stat .lbl {{ font-size: .8em; color: #666; }}
  .controls {{ margin-bottom: 12px; }}
  .controls label {{ margin-right: 16px; cursor: pointer; font-size: .9em; }}
  .query-block {{ background: #fff; border-radius: 8px; margin-bottom: 14px;
                  box-shadow: 0 1px 4px rgba(0,0,0,.08); overflow: hidden; }}
  .query-block.has-diff {{ border-left: 4px solid #e67e22; }}
  .query-header {{ padding: 10px 16px; background: #f8f9fa; border-bottom: 1px solid #eee;
                   display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
  .query-text {{ font-weight: 600; flex: 1; }}
  .timing {{ margin-left: auto; font-size: .8em; color: #888; }}
  .tables {{ display: flex; gap: 0; }}
  .half {{ flex: 1; padding: 10px 12px; border-right: 1px solid #f0f0f0; overflow-x: auto; }}
  .half:last-child {{ border-right: none; }}
  .table-label {{ font-size: .75em; font-weight: 700; color: #555;
                  text-transform: uppercase; letter-spacing: .5px; margin-bottom: 6px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: .82em; }}
  th {{ background: #f0f0f0; padding: 5px 8px; text-align: left; white-space: nowrap; }}
  td {{ padding: 5px 8px; vertical-align: top; border-bottom: 1px solid #f5f5f5; }}
  td.rank {{ width: 24px; color: #aaa; text-align: center; font-size: .85em;
             vertical-align: top; padding-top: 8px; }}
  .meta-row {{ display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin-bottom: 4px; }}
  .chu-de  {{ font-size: .72em; background: #e8f4fd; color: #1a6fa0;
              padding: 1px 6px; border-radius: 3px; white-space: nowrap; }}
  .de-muc  {{ font-size: .72em; background: #f0f0f0; color: #555;
              padding: 1px 6px; border-radius: 3px; }}
  .score-inline {{ font-size: .72em; color: #999; font-family: monospace; margin-left: auto; }}
  .tieu-de {{ font-weight: 700; font-size: .92em; margin-bottom: 5px; color: #2c3e50; }}
  .noidung {{ font-size: .84em; color: #444; line-height: 1.6; }}
  .noidung .header-meta {{ font-size: .88em; color: #888; margin-bottom: 6px; }}
  .noidung .ten-dieu {{ font-weight: 700; color: #1a3c5e; margin: 6px 0 4px; }}
  .noidung .khoan {{ margin: 8px 0 2px; font-weight: 600; color: #2c3e50; }}
  .noidung .diem  {{ margin: 2px 0 2px 20px; color: #333; }}
  .noidung .normal-line {{ margin: 2px 0; }}
  .badge.new-badge {{ background: #fff9c4; color: #7b5800; }}
  .badge.dropped-badge {{ background: #f8d7da; color: #721c24; }}
  .section-label {{ padding: 5px 16px; font-size: .78em; font-weight: 700;
                    text-transform: uppercase; letter-spacing: .5px;
                    background: #f0f4f8; color: #555; border-top: 1px solid #e8e8e8; }}
  .section-label.filtered {{ background: #fff8e1; color: #7b5800; }}
  .section-label.rewrite  {{ background: #e8f5e9; color: #2e7d32; }}
  .rewritten-query {{ padding: 4px 16px 6px; font-size: .82em; color: #555;
                      background: #f0fff0; border-bottom: 1px solid #e0f0e0; }}
  .t-ms {{ font-weight: 400; color: #aaa; font-size: .85em; margin-left: 4px; }}
  .badge.filter-badge {{ background: #fff3cd; color: #7b5800; }}
  .badge.no-filter {{ background: #f0f0f0; color: #999; }}
  td.na {{ text-align: center; color: #bbb; font-style: italic; padding: 20px; }}
  .rank-arrow {{ display:inline-block; padding: 1px 6px; border-radius: 3px;
                 font-size: .75em; font-weight: 700; white-space: nowrap; }}
  .rank-up   {{ background: #d4edda; color: #155724; }}
  .rank-down {{ background: #fce4ec; color: #721c24; }}
  .rank-same {{ background: #f0f0f0; color: #666; }}
  tr.newdoc        td {{ background: #fffde7; }}
  tr.dropped       td {{ background: #fce4ec; opacity: .6; }}
  tr.rank-improved td {{ background: #f0fff4; }}
  tr.rank-fell     td {{ background: #fff8f0; }}
  .badge {{ display: inline-block; padding: 1px 7px; border-radius: 10px;
            font-size: .72em; font-weight: 700; white-space: nowrap; }}
  .badge.changed  {{ background: #fff3cd; color: #856404; }}
  .badge.new      {{ background: #d4edda; color: #155724; }}
  .badge.new-badge {{ background: #fff9c4; color: #7b5800; }}
  .badge.dropped-badge {{ background: #f8d7da; color: #721c24; }}
  .hide-same .query-block:not(.has-diff) {{ display: none; }}
</style>
</head>
<body>
<h1>Hybrid Search Evaluation Report</h1>
<p style="color:#666;margin-top:0">{total} queries — Vector vs Hybrid (BM25 + RRF)</p>

<div class="summary">
  <div class="stat"><div class="val">{total}</div><div class="lbl">Tổng queries</div></div>
  <div class="stat"><div class="val">{n_has_new}</div><div class="lbl">Queries có docs mới từ BM25</div></div>
  <div class="stat"><div class="val">{total-n_has_new}</div><div class="lbl">Queries kết quả giống nhau</div></div>
  <div class="stat"><div class="val">{avg_t_vec:.0f}ms</div><div class="lbl">Vector avg</div></div>
  <div class="stat"><div class="val">{avg_t_hyb:.0f}ms</div><div class="lbl">Hybrid avg</div></div>
</div>

<div class="controls">
  <label><input type="checkbox" id="diffOnly" onchange="document.body.classList.toggle('hide-same',this.checked)">
    Chỉ hiện queries có sự khác biệt</label>
</div>

{entries_html}
</body>
</html>"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[DONE] Báo cáo HTML → {out_path}")
    print(f"       Mở file trong trình duyệt để xem.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="So sánh vector search vs hybrid search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd")

    p_collect = sub.add_parser("collect", help="Chạy search và lưu cache")
    p_collect.add_argument("--queries", required=True, help="File queries (1 câu/dòng)")
    p_collect.add_argument("--force", action="store_true", help="Chạy lại dù đã có cache")
    p_collect.add_argument("--no-router", action="store_true", help="Bỏ qua topic router (không cần API key)")
    p_collect.add_argument("--ollama", action="store_true", help="Hiện đã là mặc định, dùng Ollama local", default=True)
    p_collect.add_argument("--ollama-model", default="qwen2.5:3b", help="Tên model Ollama (mặc định: qwen2.5:3b)")
    p_collect.add_argument("--no-rewrite", action="store_true", help="Tắt query rewriting")

    sub.add_parser("report", help="In báo cáo tổng hợp ra terminal")

    p_detail = sub.add_parser("detail", help="Xem chi tiết 1 query")
    p_detail.add_argument("--query", required=True, help="Câu hỏi cần xem")

    p_html = sub.add_parser("html", help="Xuất báo cáo HTML")
    p_html.add_argument("--out", default=None, help="Đường dẫn file output (mặc định: eval_cache/report.html)")

    args = parser.parse_args()

    if args.cmd == "collect":
        cmd_collect(args.queries, force=args.force, no_router=args.no_router,
                    ollama_model=args.ollama_model, no_rewrite=args.no_rewrite)
    elif args.cmd == "report":
        cmd_report()
    elif args.cmd == "detail":
        cmd_detail(args.query)
    elif args.cmd == "html":
        cmd_html(args.out)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
