import json
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ValidationError

from src.agents.base_agent import AgentResult, MCPAgent
from src.agents.specialists import (
    create_leasing_agent,
    create_maintenance_agent,
    create_policy_agent,
)
from src.llm.base import LLMProvider, Message

class AgentRoute(str, Enum):
    LEASING = "leasing"
    MAINTENANCE = "maintenance"
    POLICY = "policy"

class RouteDecision(BaseModel):
    route: AgentRoute = Field(..., description="Target specialist agent")
    reasoning: str = Field(..., description="Brief explanation for routing choice")


SUPERVISOR_PROMPT = """You are the Supervisor Router for DLF Rose Property Management.
Classify the user's request and respond ONLY with valid JSON matching this schema:
{"route": "leasing" | "maintenance" | "policy", "reasoning": "<short reason>"}

Routing Rules:
- "leasing": Searching apartments, rent prices, pet/couple-friendly units, income qualification, booking tours.
- "maintenance": Broken appliances, leaks, HVAC, plumbing, electrical issues, work order status.
- "policy": Lease terms, security deposits, late fees, pet fees, quiet hours.
"""


class SupervisorOrchestrator:
    """Routes incoming requests to specialized MCP agents."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm
        self.agents: dict[AgentRoute, MCPAgent] = {
            AgentRoute.LEASING: create_leasing_agent(llm),
            AgentRoute.MAINTENANCE: create_maintenance_agent(llm),
            AgentRoute.POLICY: create_policy_agent(llm),
        }

    async def route(self, user_input: str) -> RouteDecision:
        resp = await self.llm.generate(
            messages=[Message(role="user", content=user_input)],
            system_prompt=SUPERVISOR_PROMPT,
            temperature=0.0,
        )
        try:
            data = json.loads(resp.content)
            return RouteDecision(**data)
        except (json.JSONDecodeError, ValidationError):
            # Safe fallback to policy agent if routing JSON is malformed
            return RouteDecision(route=AgentRoute.POLICY, reasoning="Fallback due to invalid router JSON")

    async def handle_request(
        self, user_input: str, history: Optional[list[Message]] = None
    ) -> tuple[RouteDecision, AgentResult]:
        decision = await self.route(user_input)
        specialist = self.agents[decision.route]
        result = await specialist.run(user_input=user_input, history=history)
        return decision, result