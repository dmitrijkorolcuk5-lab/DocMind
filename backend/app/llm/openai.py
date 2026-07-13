from collections.abc import AsyncIterator, Sequence

from openai import AsyncOpenAI, OpenAIError
from openai.types.chat import ChatCompletionMessageParam

from app.core.config import Settings
from app.core.exceptions import DependencyUnavailableError
from app.llm.base import LLMMessage


class OpenAILLMProvider:
    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.OPENAI_API_KEY.get_secret_value()
        api_key = self._api_key or "missing-key"
        self._client = AsyncOpenAI(api_key=api_key)
        self.model = settings.LLM_MODEL

    async def stream_answer(self, messages: Sequence[LLMMessage]) -> AsyncIterator[str]:
        if not self._api_key:
            raise DependencyUnavailableError("OPENAI_API_KEY is required to generate answers")
        payload: list[ChatCompletionMessageParam] = []
        for message in messages:
            if message.role == "system":
                payload.append({"role": "system", "content": message.content})
            elif message.role == "assistant":
                payload.append({"role": "assistant", "content": message.content})
            else:
                payload.append({"role": "user", "content": message.content})
        try:
            stream = await self._client.chat.completions.create(
                model=self.model,
                messages=payload,
                stream=True,
                temperature=0.2,
            )
            async for event in stream:
                delta = event.choices[0].delta.content
                if delta:
                    yield delta
        except OpenAIError as exc:
            raise DependencyUnavailableError("LLM provider failed") from exc
