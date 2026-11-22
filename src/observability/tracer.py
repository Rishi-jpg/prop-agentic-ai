import os
from typing import Any, Optional
from pydantic import BaseModel, Field

try:
    from langfuse import Langfuse
except ImportError:
    Langfuse=None

class TraceRecord(BaseModel):
    name: str
    input: str
    output: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    scores: dict[str, float] = Field(default_factory=dict)


class AgentTracer:
    """Observability wrapper that streams traces to Langfuse when configured,
    and records traces locally for zero-cost testing."""

    def __init__(self, enabled: Optional[bool] = None):
        has_keys = bool(
            os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
        )
        self.enabled = has_keys if enabled is None else (enabled and has_keys)
        self.client = Langfuse() if (self.enabled and Langfuse is not None) else None
        self.local_traces: list[TraceRecord] = []

    def log_execution(
        self,
        name: str,
        user_input: str,
        response: str,
        metadata: dict[str, Any],
        scores: Optional[dict[str, float]] = None,
    ) -> TraceRecord:
        record = TraceRecord(
            name=name,
            input=user_input,
            output=response,
            metadata=metadata,
            scores=scores or {},
        )
        self.local_traces.append(record)

        if self.client is not None:
            trace = self.client.trace(
                name=name,
                input=user_input,
                output=response,
                metadata=metadata,
            )
            for score_name, value in (scores or {}).items():
                trace.score(name=score_name, value=value)
            self.client.flush()

        return record