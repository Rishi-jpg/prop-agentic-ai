from typing import Any, Callable, Optional
from src.llm.base import LLMProvider, LLMResponse, Message


class MockLLMProvider(LLMProvider):
    """Deterministic local provider for zero-cost development and pytest suites."""

    def __init__(self, handler: Optional[Callable[[list[Message], str], LLMResponse]] = None):
        self.handler = handler
        self.call_history: list[dict[str, Any]] = []

    async def generate(
        self,
        messages: list[Message],
        system_prompt: str,
        tools: Optional[list[dict[str, Any]]] = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        self.call_history.append({
            "system_prompt": system_prompt,
            "messages": messages,
            "tools": tools,
        })
        if self.handler:
            return self.handler(messages, system_prompt)
        return LLMResponse(content=f"[MOCK] Received: {messages[-1].content}")