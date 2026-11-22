import json
import pytest
from evals.run_evals import run_evaluation
from src.llm.base import LLMResponse, Message, ToolCall
from src.llm.mock_provider import MockLLMProvider
from src.observability.tracer import AgentTracer


@pytest.mark.asyncio
async def test_golden_eval_suite_and_tracing():
    def mock_handler(messages: list[Message], system_prompt: str) -> LLMResponse:
        last_msg = messages[-1].content.lower()

        if "Supervisor Router" in system_prompt:
            if "pipe" in last_msg or "sink" in last_msg:
                return LLMResponse(content=json.dumps({"route": "maintenance", "reasoning": "Leak"}))
            if "apartment" in last_msg:
                return LLMResponse(content=json.dumps({"route": "leasing", "reasoning": "Unit search"}))
            return LLMResponse(content=json.dumps({"route": "policy", "reasoning": "Policy FAQ"}))

        if "Leasing Specialist" in system_prompt and messages[-1].role == "user":
            return LLMResponse(
                tool_calls=[
                    ToolCall(
                        id="eval_t1",
                        name="search_available_units",
                        arguments={"max_rent": 2500.0, "pet_friendly": True, "couple_friendly": True},
                    )
                ]
            )

        if "Maintenance Triage" in system_prompt and messages[-1].role == "user":
            return LLMResponse(
                tool_calls=[
                    ToolCall(
                        id="eval_t2",
                        name="create_work_order",
                        arguments={
                            "unit_id": "BLDG-A-302",
                            "tenant_name": "Tenant",
                            "category": "plumbing",
                            "description": "Burst pipe",
                            "priority": "emergency",
                            "estimated_cost": 750.0,
                        },
                    )
                ]
            )

        return LLMResponse(content="Handled according to Oakridge policy.")

    tracer = AgentTracer(enabled=False)  # Local-only mode for CI
    summary = await run_evaluation(llm=MockLLMProvider(handler=mock_handler), tracer=tracer)

    assert summary.total_cases == 5
    assert summary.passed_cases == 5
    assert summary.pass_rate == 1.0
    # 5 harness traces + 5 eval score traces = 10 local trace records
    assert len(tracer.local_traces) == 10