import asyncio
import time
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field

from src.agents.supervisor import AgentRoute, SupervisorOrchestrator
from src.harness.guardrails import check_input_guardrails, redact_output_pii
from src.llm.base import Message
from src.observability.tracer import AgentTracer


class ExecutionStatus(str, Enum):
    COMPLETED = "completed"
    BLOCKED = "blocked"
    PENDING_APPROVAL = "pending_approval"
    TIMEOUT = "timeout"


class HarnessResponse(BaseModel):
    status: ExecutionStatus
    response: str
    route: Optional[AgentRoute] = None
    agent_name: Optional[str] = None
    requires_human_approval: bool = False
    approval_payload: Optional[dict[str, Any]] = None
    tool_calls_made: list[dict[str, Any]] = Field(default_factory=list)
    total_tokens: int = 0
    latency_ms: float = 0.0
    audit_events: list[str] = Field(default_factory=list)


class AgentHarness:
    """Deterministic production wrapper around the Multi-Agent Orchestrator."""

    def __init__(
        self,
        orchestrator: SupervisorOrchestrator,
        compliance_region: str = "IN",
        timeout_seconds: float = 20.0,
        max_token_budget: int = 8000,
        tracer: Optional[AgentTracer] = None,
    ):
        self.orchestrator = orchestrator
        self.compliance_region = compliance_region
        self.timeout_seconds = timeout_seconds
        self.max_token_budget = max_token_budget
        self.tracer = tracer

    def _record_trace(self, user_input: str, result: HarnessResponse) -> HarnessResponse:
        """Send execution metadata to Langfuse / local tracer if configured."""
        if self.tracer:
            self.tracer.log_execution(
                name="property_agent_execution",
                user_input=user_input,
                response=result.response,
                metadata={
                    "status": result.status.value,
                    "route": result.route.value if result.route else None,
                    "agent_name": result.agent_name,
                    "requires_human_approval": result.requires_human_approval,
                    "tool_calls": [tc["tool"] for tc in result.tool_calls_made],
                    "total_tokens": result.total_tokens,
                    "latency_ms": result.latency_ms,
                    "audit_events": result.audit_events,
                },
            )
        return result

    async def execute(
        self, user_input: str, history: Optional[list[Message]] = None
    ) -> HarnessResponse:
        start = time.perf_counter()
        audit_events: list[str] = []

        # 1. Input Guardrail Gate
        guard = check_input_guardrails(user_input, compliance_region=self.compliance_region)
        if not guard.allowed:
            audit_events.append(f"INPUT_BLOCKED: {guard.reason}")
            return self._record_trace(
                user_input,
                HarnessResponse(
                    status=ExecutionStatus.BLOCKED,
                    response=f"I cannot process this request. ({guard.reason})",
                    latency_ms=round((time.perf_counter() - start) * 1000, 2),
                    audit_events=audit_events,
                ),
            )
        audit_events.append("INPUT_GUARDRAIL_PASSED")

        # 2. Execute Orchestrator with Timeout Circuit Breaker
        try:
            decision, result = await asyncio.wait_for(
                self.orchestrator.handle_request(user_input=user_input, history=history),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            audit_events.append(f"CIRCUIT_BREAKER_TIMEOUT: >{self.timeout_seconds}s")
            return self._record_trace(
                user_input,
                HarnessResponse(
                    status=ExecutionStatus.TIMEOUT,
                    response="The request took too long to process. Please try again or contact support.",
                    latency_ms=round((time.perf_counter() - start) * 1000, 2),
                    audit_events=audit_events,
                ),
            )

        audit_events.append(f"ROUTED_TO:{decision.route.value}")

        # 3. Token Budget Audit
        if result.total_tokens > self.max_token_budget:
            audit_events.append(
                f"TOKEN_BUDGET_EXCEEDED:{result.total_tokens}/{self.max_token_budget}"
            )

        # 4. Deterministic HITL Approval Gate (inspects MCP tool outputs directly)
        approval_payload = None
        for tc in result.tool_calls_made:
            output = tc.get("output")
            if isinstance(output, dict) and output.get("requires_human_approval") is True:
                approval_payload = {
                    "tool": tc["tool"],
                    "ticket_id": output.get("ticket_id"),
                    "estimated_cost": output.get("estimated_cost"),
                    "priority": output.get("priority"),
                }
                audit_events.append(f"HITL_TRIGGERED:{output.get('ticket_id')}")
                break

        # 5. Output PII Redaction
        safe_response = redact_output_pii(result.response)
        if safe_response != result.response:
            audit_events.append("OUTPUT_PII_REDACTED")

        status = (
            ExecutionStatus.PENDING_APPROVAL
            if approval_payload
            else ExecutionStatus.COMPLETED
        )

        return self._record_trace(
            user_input,
            HarnessResponse(
                status=status,
                response=safe_response,
                route=decision.route,
                agent_name=result.agent_name,
                requires_human_approval=approval_payload is not None,
                approval_payload=approval_payload,
                tool_calls_made=result.tool_calls_made,
                total_tokens=result.total_tokens,
                latency_ms=round((time.perf_counter() - start) * 1000, 2),
                audit_events=audit_events,
            ),
        )