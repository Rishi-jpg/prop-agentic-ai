from ast import arguments
from abc import ABC, abstractmethod
from typing import Any, Optional
from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    id:str
    name:str
    arguments: dict[str,Any]

class Message(BaseModel):
    role: str = Field(..., description="'user', 'assistant' or 'tool'")
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_call_id: Optional[str] = None

class LLMResponse(BaseModel):
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = "end_turn"

class LLMProvider(ABC):
    """Vendor-agnostic interface for all LLM interactions."""

    @abstractmethod
    async def generate(
        self,
        messages: list[Message],
        system_prompt: str,
        tools: Optional[list[dict[str, Any]]] = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Send messages + optional tool schemas and return a normalized response."""
        pass