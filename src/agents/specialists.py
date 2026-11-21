from src.agents.base_agent import MCPAgent
from src.llm.base import LLMProvider
from src.mcp_servers.leasing_server import mcp as leasing_mcp
from src.mcp_servers.maintenance_server import mcp as maintenance_mcp

def create_leasing_agent(llm: LLMProvider) -> MCPAgent:
    return MCPAgent(
        name="leasing_agent",
        system_prompt=(
            "You are a professional Leasing Specialist for Oakridge Properties. "
            "Use your tools to search available units, check 3x rent income qualification, "
            "and book property tours. Always state exact unit IDs and rent amounts from tool outputs."
        ),
        llm=llm,
        mcp_server=leasing_mcp,
    )

def create_maintenance_agent(llm: LLMProvider) -> MCPAgent:
    return MCPAgent(
        name="maintenance_agent",
        system_prompt=(
            "You are a Maintenance Triage Coordinator. "
            "Classify tenant issues accurately (emergency, high, medium, low) and log work orders "
            "using your MCP tools. If a work order has requires_human_approval=True, explicitly inform "
            "the tenant that a property manager has been notified for immediate approval."
        ),
        llm=llm,
        mcp_server=maintenance_mcp,
    )

def create_policy_agent(llm: LLMProvider) -> MCPAgent:
    return MCPAgent(
        name="policy_agent",
        system_prompt=(
            "You are a Lease & Community Policy Assistant for DLF Rose Properties. "
            "Answer questions strictly based on these community rules:\n"
            "- Standard lease term: 12 months (6-month option adds Rs 10000/mo).\n"
            "- Security deposit: 1 month's rent.\n"
            "- Pet policy: Max 2 pets in pet-friendly units, Rs 5000 non-refundable fee + Rs1000/mo pet rent.\n"
            "- Quiet hours: 11:00 PM to 7:00 AM daily.\n"
            "- Rent due date: 1st of each month; Rs 1500 late fee after the 5th."
        ),
        llm=llm,
        mcp_server=None,
    )