from app.core.config import Settings
from app.llm.base import LLMProvider
from app.llm.gemini import GeminiLLMProvider
from app.llm.openai import OpenAILLMProvider


def build_llm_provider(settings: Settings) -> LLMProvider:
    if settings.LLM_PROVIDER == "openai":
        return OpenAILLMProvider(settings)
    return GeminiLLMProvider(settings)
