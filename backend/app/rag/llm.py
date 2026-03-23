import os
from pathlib import Path
from google import genai
from google.genai import types
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


class GeminiLLM:
    """Gemini LLM provider dùng Google Gen AI SDK"""

    def __init__(self):
        api_key = _read_env_key("GEMINI_API_KEY") or settings.GEMINI_API_KEY
        if not api_key:
            raise ValueError("GEMINI_API_KEY chưa được cấu hình trong file .env")
        self._client = genai.Client(api_key=api_key)
        self._model = _read_env_key("LLM_MODEL") or settings.LLM_MODEL

    def generate(self, prompt: str) -> str:
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=settings.LLM_TEMPERATURE,
                max_output_tokens=settings.LLM_MAX_TOKENS,
            ),
        )
        if not response.text:
            return "Không thể tạo câu trả lời cho câu hỏi này. Vui lòng thử diễn đạt lại câu hỏi."
        return response.text

    def rewrite_query(self, query: str) -> str:
        prompt = REWRITE_PROMPT.format(question=query)
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=128),
        )
        rewritten = (response.text or "").strip()
        return rewritten if rewritten else query

    def generate_with_context(self, query: str, context: str) -> str:
        prompt = PROMPT_TEMPLATE.format(context=context, question=query)
        return self.generate(prompt)


class LLMManager:
    def __init__(self):
        self.llm = self._init_llm()

    def _init_llm(self):
        if settings.LLM_PROVIDER == "gemini":
            return GeminiLLM()
        raise ValueError(f"LLM provider không hỗ trợ: {settings.LLM_PROVIDER}")

    def rewrite_query(self, query: str) -> str:
        return self.llm.rewrite_query(query)

    def generate_answer(self, query: str, context: str) -> str:
        return self.llm.generate_with_context(query, context)

    def generate(self, prompt: str) -> str:
        return self.llm.generate(prompt)


llm_manager = None


def reset_llm_manager():
    global llm_manager
    _load_env_cache()  # Tải lại .env để lấy key mới nhất
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
