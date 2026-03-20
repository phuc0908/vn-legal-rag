import os
from pathlib import Path
from google import genai
from google.genai import types
from app.core.config import settings

_ENV_FILE = Path(__file__).parent.parent.parent / ".env"

def _read_env_key(key: str) -> str:
    """Đọc trực tiếp từ file .env để lấy giá trị mới nhất."""
    val = os.environ.get(key)
    if val:
        return val
    if _ENV_FILE.exists():
        for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip()
    return ""


PROMPT_TEMPLATE = """Bạn là một trợ lý pháp lý thông minh chuyên về **pháp luật Việt Nam**.

Phạm vi hỗ trợ: Trả lời các câu hỏi thuộc mọi lĩnh vực pháp luật Việt Nam, bao gồm nhưng không giới hạn:
hình sự, dân sự, đất đai, lao động, doanh nghiệp, hành chính, hôn nhân gia đình, tố tụng, v.v.
Nếu câu hỏi hoàn toàn không liên quan đến pháp luật, hãy lịch sự giải thích và đề nghị người dùng đặt câu hỏi pháp lý.

VĂN BẢN PHÁP LUẬT LIÊN QUAN TÌM ĐƯỢC:
{context}

CÂU HỎI: {question}

HƯỚNG DẪN TRẢ LỜI:
- Nếu có văn bản pháp luật liên quan ở trên, hãy ưu tiên trả lời dựa trên các văn bản đó, trích dẫn tên văn bản và số điều cụ thể nếu có.
- Nếu văn bản tìm được không liên quan hoặc không đủ, hãy trả lời dựa trên kiến thức tổng quát về pháp luật Việt Nam và ghi chú rõ: "(Dựa trên kiến thức tổng quát, không có văn bản cụ thể trong cơ sở dữ liệu)".
- Trả lời chi tiết, có cấu trúc rõ ràng với các mục, tiêu đề in đậm.
- Chỉ dùng Markdown, không dùng thẻ HTML.
- Giải thích các thuật ngữ pháp lý nếu cần thiết.

TRẢ LỜI:"""


class GeminiLLM:
    """Gemini LLM provider dùng Google Gen AI SDK"""

    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY chưa được cấu hình trong file .env")

    def generate(self, prompt: str) -> str:
        client = genai.Client(api_key=_read_env_key("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model=_read_env_key("LLM_MODEL") or settings.LLM_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=settings.LLM_TEMPERATURE,
                max_output_tokens=settings.LLM_MAX_TOKENS,
            ),
        )
        return response.text

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

    def generate_answer(self, query: str, context: str) -> str:
        return self.llm.generate_with_context(query, context)

    def generate(self, prompt: str) -> str:
        return self.llm.generate(prompt)


llm_manager = None


def reset_llm_manager():
    global llm_manager
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
