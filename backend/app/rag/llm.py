import os
import re
from pathlib import Path
from typing import Optional
import requests
from app.core.config import settings

_ENV_FILE = Path(__file__).parent.parent.parent / ".env"
_env_cache: dict = {}


def _load_env_cache():
    """Nạp (hoặc tải lại) các biến từ file .env vào cache."""
    global _env_cache
    cache = {}
    if _ENV_FILE.exists():
        for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                cache[k.strip()] = v.strip()
    _env_cache = cache


def _read_env_key(key: str) -> str:
    """Đọc từ biến môi trường, fallback sang cache file .env."""
    val = os.environ.get(key)
    if val:
        return val
    if not _env_cache:
        _load_env_cache()
    return _env_cache.get(key, "")


REWRITE_PROMPT = """Hãy viết lại câu hỏi sau thành một truy vấn pháp lý ngắn gọn, dùng thuật ngữ pháp luật Việt Nam chính thức để tìm kiếm trong cơ sở dữ liệu văn bản pháp luật.

Yêu cầu:
- Chỉ trả về đúng 1 câu truy vấn, không giải thích
- Dùng thuật ngữ pháp lý chính thức (tên tội danh, tên luật, điều khoản...)
- Giữ nguyên chủ đề pháp lý của câu hỏi gốc

Câu hỏi gốc: {question}

Truy vấn pháp lý:"""

REWRITE_WITH_HISTORY_PROMPT = """Bạn là trợ lý pháp lý. Dựa trên lịch sử hội thoại bên dưới và câu hỏi mới, hãy viết lại câu hỏi mới thành một truy vấn pháp lý độc lập, đầy đủ ngữ cảnh.

Lịch sử hội thoại gần đây:
{history}

Câu hỏi mới: {question}

Yêu cầu:
- Nếu câu hỏi dùng đại từ ("nó", "điều đó", "như trên", "vấn đề này"...) hãy thay thế bằng nội dung cụ thể từ lịch sử
- Nếu câu hỏi là tiếp nối ("còn nếu...", "thế thì...", "vậy...") hãy khai triển thành câu hỏi đầy đủ
- Chỉ trả về đúng 1 câu truy vấn pháp lý, không giải thích

Truy vấn pháp lý:"""

SYSTEM_LEGAL_PROMPT = """Bạn là một trợ lý pháp lý chuyên về **pháp luật Việt Nam**.

VĂN BẢN PHÁP LUẬT LIÊN QUAN TÌM ĐƯỢC:
{context}

NGUYÊN TẮC TRẢ LỜI (bắt buộc tuân thủ):
- Nếu có văn bản pháp luật ở trên, ưu tiên trả lời dựa trên các văn bản đó và trích dẫn rõ nguồn.
- Nếu văn bản tìm được không đủ hoặc không có, hãy trả lời dựa trên kiến thức pháp luật Việt Nam của bạn và ghi rõ "(dựa trên kiến thức pháp luật chung)".
- Trả lời có cấu trúc rõ ràng, dùng tiêu đề in đậm và danh sách khi cần.
- Chỉ dùng Markdown, không dùng thẻ HTML."""

# Giữ lại để tương thích với single-turn (khi không có history)
PROMPT_TEMPLATE = """Bạn là một trợ lý pháp lý chuyên về **pháp luật Việt Nam**.

VĂN BẢN PHÁP LUẬT LIÊN QUAN TÌM ĐƯỢC:
{context}

CÂU HỎI: {question}

NGUYÊN TẮC TRẢ LỜI (bắt buộc tuân thủ):
- Nếu có văn bản pháp luật ở trên, ưu tiên trả lời dựa trên các văn bản đó và trích dẫn rõ nguồn.
- Nếu văn bản tìm được không đủ hoặc không có, hãy trả lời dựa trên kiến thức pháp luật Việt Nam của bạn và ghi rõ "(dựa trên kiến thức pháp luật chung)".
- Trả lời có cấu trúc rõ ràng, dùng tiêu đề in đậm và danh sách khi cần.
- Chỉ dùng Markdown, không dùng thẻ HTML.

TRẢ LỜI:"""

# Số lượt hội thoại tối đa giữ trong context (1 lượt = 1 user + 1 assistant)
MAX_HISTORY_TURNS = 3


class GroqLLM:

    def __init__(self):
        self._api_key = _read_env_key("GROQ_API_KEY") or settings.GROQ_API_KEY
        if not self._api_key:
            raise ValueError("GROQ_API_KEY chưa được cấu hình trong file .env")
        self._model = _read_env_key("LLM_MODEL") or settings.LLM_MODEL
        self._url = "https://api.groq.com/openai/v1/chat/completions"

    def _call(self, prompt: str = None, messages: list = None,
              temperature: float = None, max_tokens: int = None) -> str:
        """Gọi Groq API.

        Truyền `messages` để dùng multi-turn (system + history + user).
        Truyền `prompt` để dùng single-turn đơn giản.
        """
        if messages is None:
            messages = [{"role": "user", "content": prompt}]
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature if temperature is not None else settings.LLM_TEMPERATURE,
            "max_tokens": max_tokens if max_tokens is not None else settings.LLM_MAX_TOKENS,
        }
        resp = requests.post(self._url, json=payload, headers=headers, timeout=60)
        if not resp.ok:
            print(f"[GROQ ERROR] {resp.status_code}: {resp.text}")
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    def generate(self, prompt: str = None, messages: list = None) -> str:
        try:
            result = self._call(prompt=prompt, messages=messages)
            return result or "Không thể tạo câu trả lời. Vui lòng thử lại."
        except Exception as e:
            err = str(e)
            if "429" in err:
                return "Hệ thống đang bận, vui lòng thử lại sau."
            raise

    def rewrite_query(self, query: str, history: list = None) -> str:
        """Viết lại query. Nếu có history, giải quyết đại từ/tham chiếu."""
        if history:
            # Tóm tắt history thành text để đưa vào prompt rewrite
            history_text = "\n".join(
                f"{'Người dùng' if t.role == 'user' else 'Trợ lý'}: {t.content[:200]}"
                for t in history[-(MAX_HISTORY_TURNS * 2):]
            )
            prompt = REWRITE_WITH_HISTORY_PROMPT.format(history=history_text, question=query)
        else:
            prompt = REWRITE_PROMPT.format(question=query)
        try:
            return self._call(prompt=prompt, temperature=0.1, max_tokens=128) or query
        except Exception:
            return query

    def generate_with_context(self, query: str, context: str, history: list = None) -> str:
        """Sinh câu trả lời. Nếu có history, dùng multi-turn messages."""
        if history:
            # System message chứa RAG context và nguyên tắc trả lời
            messages = [{"role": "system", "content": SYSTEM_LEGAL_PROMPT.format(context=context)}]
            # Thêm các lượt hội thoại trước (giới hạn MAX_HISTORY_TURNS lượt)
            for turn in history[-(MAX_HISTORY_TURNS * 2):]:
                # Cắt assistant messages dài để tiết kiệm token
                content = turn.content[:600] if turn.role == "assistant" else turn.content
                messages.append({"role": turn.role, "content": content})
            # Câu hỏi hiện tại
            messages.append({"role": "user", "content": query})
            print(f"  [LLM] Multi-turn: system + {len(messages)-2} history msgs + 1 user")
            return self.generate(messages=messages)
        else:
            prompt = PROMPT_TEMPLATE.format(context=context, question=query)
            return self.generate(prompt=prompt)


class LLMManager:
    def __init__(self):
        self.llm = self._init_llm()

    def _init_llm(self):
        provider = _read_env_key("LLM_PROVIDER") or settings.LLM_PROVIDER
        if provider == "groq":
            return GroqLLM()
        raise ValueError(f"LLM provider không hỗ trợ: {provider}")

    def rewrite_query(self, query: str, history: list = None) -> str:
        return self.llm.rewrite_query(query, history=history)

    def generate_answer(self, query: str, context: str, history: list = None) -> str:
        return self.llm.generate_with_context(query, context, history=history)

    def generate(self, prompt: str) -> str:
        return self.llm.generate(prompt=prompt)


llm_manager = None


def reset_llm_manager():
    global llm_manager
    _load_env_cache()
    llm_manager = None


def get_llm_manager() -> LLMManager:
    global llm_manager
    if llm_manager is None:
        try:
            llm_manager = LLMManager()
        except ValueError as e:
            print(f"Warning: {e}")
            return None
    return llm_manager


# ── Hierarchical RAG: Topic Router ───────────────────────────────────────────

TOPIC_ROUTER_PROMPT = """Bạn là chuyên gia phân loại văn bản pháp luật Việt Nam.
Nhiệm vụ: Dựa trên câu hỏi, hãy chọn CHỦ ĐỀ PHÁP LÝ phù hợp nhất.

DANH SÁCH CHỦ ĐỀ:
{topic_list}

CÂU HỎI: {question}

LƯU Ý QUAN TRỌNG:
- Nếu câu hỏi nhắc đến "Bộ luật tố tụng hình sự" hoặc "Bộ luật hình sự" -> Phải chọn "Hình sự".
- Nếu câu hỏi nhắc đến "Bộ luật tố tụng dân sự" hoặc "Bộ luật dân sự" -> Phải chọn "Dân sự".
- Nếu câu hỏi nhắc đến "Luật đất đai" -> Phải chọn "Đất đai".
- Kiểm tra kỹ các từ khóa chuyên môn trong câu hỏi để đối chiếu với danh sách chủ đề.

YÊU CẦU PHẢN HỒI:
- Chỉ trả về duy nhất 1 con số là ID của chủ đề (ví dụ: 5).
- Nếu hoàn toàn không có chủ đề nào phù hợp, trả về 0.
- Tuyệt đối không giải thích thêm.

ID chủ đề:"""


class TopicRouter:
    """Routes queries to the most relevant legal topic (chu_de) using LLM classification.

    This is the first layer of the Hierarchical RAG architecture:
    Query → topic routing → bounded subset retrieval → generation
    """

    def __init__(self, llm: GroqLLM, topics: list):
        self.llm = llm
        # Map: str(id) → ten (topic name)
        self._topic_map: dict = {str(t["id"]): t["ten"] for t in topics}
        # Map: số thứ tự (1-based) → uuid — để LLM trả về số thay vì UUID
        self._idx_to_uuid: dict = {str(i): str(t["id"]) for i, t in enumerate(topics, 1)}
        self._topic_list_str: str = "\n".join(
            f"  {i}: {t['ten']}" for i, t in enumerate(topics, 1)
        )
        print(f"[ROUTER] Khởi tạo TopicRouter với {len(topics)} chủ đề: "
              + ", ".join(f"{t['id']}={t['ten']}" for t in topics))

    def route(self, query: str) -> Optional[str]:
        """Classify query into a chu_de_id string, or None if no match / on error."""
        if not self._topic_map:
            return None
        prompt = TOPIC_ROUTER_PROMPT.format(
            topic_list=self._topic_list_str,
            question=query,
        )
        try:
            raw = self.llm._call(prompt, temperature=0.0, max_tokens=10)
            # LLM trả về số thứ tự (1-based), map ngược lại UUID
            match = re.search(r"\d+", raw.strip())
            if not match:
                return None
            idx = match.group(0)
            if idx == "0":
                print(f"  [ROUTER] Không khớp chủ đề nào → tìm kiếm toàn bộ")
                return None
            topic_id = self._idx_to_uuid.get(idx)
            if topic_id and topic_id in self._topic_map:
                print(f"  [ROUTER] → ID={topic_id} ({self._topic_map[topic_id]})")
                return topic_id
        except Exception as e:
            print(f"  [ROUTER] Lỗi phân loại topic: {e}")
        return None
