from pydantic import BaseModel

from evals.golden_dataset import GOLDEN_DATASET, EvalCase
from src.agents.supervisor import SupervisorOrchestrator
from src.harness.agent_harness import AgentHarness
from src.llm.base import LLMProvider
from src.observability.tracer import AgentTracer


class CaseScore(BaseModel):
    case_id: str
    status_match: bool
    route_match: bool
    tool_match: bool
    hitl_match: bool
    passed: bool


class EvalSummary(BaseModel):
    total_cases: int
    passed_cases: int
    pass_rate: float
    results: list[CaseScore]


async def run_evaluation(
    llm: LLMProvider,
    cases: list[EvalCase] = GOLDEN_DATASET,
    tracer: AgentTracer | None = None,
) -> EvalSummary:
    tracer = tracer or AgentTracer()
    orchestrator = SupervisorOrchestrator(llm=llm)
    results: list[CaseScore] = []

    for case in cases:
        harness = AgentHarness(
            orchestrator=orchestrator,
            compliance_region="IN",
            tracer=tracer,
        )
        res = await harness.execute(case.user_input)

        tools_used = [tc["tool"] for tc in res.tool_calls_made]
        status_ok = res.status == case.expected_status
        route_ok = case.expected_route is None or res.route == case.expected_route
        tool_ok = case.expected_tool is None or case.expected_tool in tools_used
        hitl_ok = res.requires_human_approval == case.expected_hitl
        passed = all([status_ok, route_ok, tool_ok, hitl_ok])

        # Log eval scores to Langfuse / local tracer
        tracer.log_execution(
            name=f"eval:{case.case_id}",
            user_input=case.user_input,
            response=res.response,
            metadata={"case_id": case.case_id, "status": res.status.value},
            scores={
                "status_match": float(status_ok),
                "route_match": float(route_ok),
                "tool_match": float(tool_ok),
                "hitl_match": float(hitl_ok),
                "overall_pass": float(passed),
            },
        )

        results.append(
            CaseScore(
                case_id=case.case_id,
                status_match=status_ok,
                route_match=route_ok,
                tool_match=tool_ok,
                hitl_match=hitl_ok,
                passed=passed,
            )
        )

    passed_count = sum(1 for r in results if r.passed)
    return EvalSummary(
        total_cases=len(results),
        passed_cases=passed_count,
        pass_rate=round(passed_count / len(results), 2) if results else 0.0,
        results=results,
    )