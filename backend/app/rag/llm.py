import os
from pathlib import Path
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


class GroqLLM:

    def __init__(self):
        self._api_key = _read_env_key("GROQ_API_KEY") or settings.GROQ_API_KEY
        if not self._api_key:
            raise ValueError("GROQ_API_KEY chưa được cấu hình trong file .env")
        self._model = _read_env_key("LLM_MODEL") or settings.LLM_MODEL
        self._url = "https://api.groq.com/openai/v1/chat/completions"

    def _call(self, prompt: str, temperature: float = None, max_tokens: int = None) -> str:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature if temperature is not None else settings.LLM_TEMPERATURE,
            "max_tokens": max_tokens if max_tokens is not None else settings.LLM_MAX_TOKENS,
        }
        resp = requests.post(self._url, json=payload, headers=headers, timeout=60)
        if not resp.ok:
            print(f"[GROQ ERROR] {resp.status_code}: {resp.text}")
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    def generate(self, prompt: str) -> str:
        try:
            result = self._call(prompt)
            return result or "Không thể tạo câu trả lời. Vui lòng thử lại."
        except Exception as e:
            err = str(e)
            if "429" in err:
                return "Hệ thống đang bận, vui lòng thử lại sau."
            raise

    def rewrite_query(self, query: str) -> str:
        prompt = REWRITE_PROMPT.format(question=query)
        try:
            return self._call(prompt, temperature=0.1, max_tokens=128) or query
        except Exception:
            return query

    def generate_with_context(self, query: str, context: str) -> str:
        prompt = PROMPT_TEMPLATE.format(context=context, question=query)
        return self.generate(prompt)


class LLMManager:
    def __init__(self):
        self.llm = self._init_llm()

    def _init_llm(self):
        provider = _read_env_key("LLM_PROVIDER") or settings.LLM_PROVIDER
        if provider == "groq":
            return GroqLLM()
        raise ValueError(f"LLM provider không hỗ trợ: {provider}")

    def rewrite_query(self, query: str) -> str:
        return self.llm.rewrite_query(query)

    def generate_answer(self, query: str, context: str) -> str:
        return self.llm.generate_with_context(query, context)

    def generate(self, prompt: str) -> str:
        return self.llm.generate(prompt)


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
