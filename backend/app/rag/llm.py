import os
import google.generativeai as genai
from app.core.config import settings


PROMPT_TEMPLATE = """Bạn là một trợ lý pháp lý thông minh chuyên về luật pháp Việt Nam.

Dựa vào các điều luật sau đây, hãy trả lời câu hỏi một cách chi tiết và chính xác.
Nếu thông tin không đủ để trả lời, hãy nói rõ điều đó.

ĐIỀU LUẬT LIÊN QUAN:
{context}

CÂU HỎI: {question}

TRẢ LỜI:"""


class GeminiLLM:
    """Gemini LLM provider dùng Google Generative AI SDK"""

    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY chưa được cấu hình trong file .env")

        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name=settings.LLM_MODEL,
            generation_config=genai.GenerationConfig(
                temperature=settings.LLM_TEMPERATURE,
                max_output_tokens=settings.LLM_MAX_TOKENS,
            )
        )

    def generate(self, prompt: str) -> str:
        """Gửi prompt và nhận câu trả lời từ Gemini"""
        response = self.model.generate_content(prompt)
        return response.text

    def generate_with_context(self, query: str, context: str) -> str:
        """Trả lời câu hỏi dựa trên context từ RAG"""
        prompt = PROMPT_TEMPLATE.format(context=context, question=query)
        return self.generate(prompt)


class LLMManager:
    """Quản lý LLM provider"""

    def __init__(self):
        self.llm = self._init_llm()

    def _init_llm(self):
        if settings.LLM_PROVIDER == "gemini":
            return GeminiLLM()
        else:
            raise ValueError(f"LLM provider không hỗ trợ: {settings.LLM_PROVIDER}")

    def generate_answer(self, query: str, context: str) -> str:
        return self.llm.generate_with_context(query, context)

    def generate(self, prompt: str) -> str:
        return self.llm.generate(prompt)


# Global instance
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
