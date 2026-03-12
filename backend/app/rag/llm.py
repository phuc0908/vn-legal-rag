from abc import ABC, abstractmethod
from typing import Optional, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from app.core.config import settings


class BaseLLM(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    def generate_with_context(self, query: str, context: str) -> str:
        pass


class OpenAILLM(BaseLLM):
    """OpenAI LLM provider"""

    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured")

        self.llm = ChatOpenAI(
            model_name=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            openai_api_key=settings.OPENAI_API_KEY
        )

        self.rag_prompt_template = PromptTemplate(
            input_variables=["context", "question"],
            template="""Bạn là một trợ lý pháp lý thông minh chuyên về luật pháp Việt Nam.

Dựa vào thông tin sau đây, hãy trả lời câu hỏi một cách chi tiết và chính xác:

THÔNG TIN LIÊN QUAN:
{context}

CÂU HỎI: {question}

TRẢ LỜI:"""
        )

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt"""
        response = self.llm.predict(text=prompt)
        return response

    def generate_with_context(self, query: str, context: str) -> str:
        """Generate answer with retrieved context"""
        prompt = self.rag_prompt_template.format(
            context=context,
            question=query
        )
        return self.generate(prompt)


class LLMManager:
    """LLM manager for handling different providers"""

    def __init__(self):
        self.llm = self._init_llm()

    def _init_llm(self) -> BaseLLM:
        """Initialize LLM based on configuration"""
        if settings.LLM_PROVIDER == "openai":
            return OpenAILLM()
        else:
            raise ValueError(f"Unknown LLM provider: {settings.LLM_PROVIDER}")

    def generate_answer(self, query: str, context: str) -> str:
        """Generate answer for a query with context"""
        return self.llm.generate_with_context(query, context)

    def generate(self, prompt: str) -> str:
        """Generate text from prompt"""
        return self.llm.generate(prompt)


# Global LLM instance
llm_manager = None


def get_llm_manager() -> LLMManager:
    """Get or create LLM manager instance"""
    global llm_manager
    if llm_manager is None:
        try:
            llm_manager = LLMManager()
        except ValueError as e:
            print(f"Warning: {e}")
            return None
    return llm_manager
