import json
import pytest

from src.agents.supervisor import AgentRoute, SupervisorOrchestrator
from src.llm.base import LLMResponse, Message, ToolCall
from src.llm.mock_provider import MockLLMProvider


@pytest.mark.asyncio
async def test_supervisor_routes_and_calls_leasing_mcp():
    def mock_llm_handler(messages: list[Message], system_prompt: str) -> LLMResponse:
        # 1. Supervisor routing call
        if "Supervisor Router" in system_prompt:
            return LLMResponse(
                content=json.dumps({"route": "leasing", "reasoning": "User wants to find an apartment"})
            )

        # 2. Leasing agent: first turn -> call MCP tool
        if messages[-1].role == "user":
            return LLMResponse(
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        name="search_available_units",
                        arguments={"max_rent": 2500.0, "couple_friendly": True},
                    )
                ]
            )

        # 3. Leasing agent: second turn -> summarize real MCP tool output
        tool_data = json.loads(messages[-1].content)
        unit_id = tool_data[0]["unit_id"]
        return LLMResponse(content=f"Unit {unit_id} is available and couple-friendly.")

    orchestrator = SupervisorOrchestrator(llm=MockLLMProvider(handler=mock_llm_handler))
    decision, result = await orchestrator.handle_request("Find me a couple-friendly apartment under $2500")

    assert decision.route == AgentRoute.LEASING
    assert result.agent_name == "leasing_agent"
    assert len(result.tool_calls_made) == 1
    assert result.tool_calls_made[0]["tool"] == "search_available_units"
    assert "BLDG-A-302" in result.response


@pytest.mark.asyncio
async def test_supervisor_routes_and_calls_maintenance_mcp():
    def mock_llm_handler(messages: list[Message], system_prompt: str) -> LLMResponse:
        if "Supervisor Router" in system_prompt:
            return LLMResponse(
                content=json.dumps({"route": "maintenance", "reasoning": "Emergency water leak"})
            )

        if messages[-1].role == "user":
            return LLMResponse(
                tool_calls=[
                    ToolCall(
                        id="call_2",
                        name="create_work_order",
                        arguments={
                            "unit_id": "BLDG-A-302",
                            "tenant_name": "Rishi",
                            "category": "plumbing",
                            "description": "Burst pipe in bathroom",
                            "priority": "emergency",
                            "estimated_cost": 700.0,
                        },
                    )
                ]
            )

        order = json.loads(messages[-1].content)
        return LLMResponse(
            content=f"Created emergency ticket {order['ticket_id']}. Manager approval required: {order['requires_human_approval']}."
        )

    orchestrator = SupervisorOrchestrator(llm=MockLLMProvider(handler=mock_llm_handler))
    decision, result = await orchestrator.handle_request("My bathroom pipe burst in BLDG-A-302!")

    assert decision.route == AgentRoute.MAINTENANCE
    assert result.agent_name == "maintenance_agent"
    assert result.tool_calls_made[0]["output"]["requires_human_approval"] is True
    assert "Manager approval required: True" in result.response