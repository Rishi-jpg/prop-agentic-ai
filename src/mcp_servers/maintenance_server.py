import uuid
from fastmcp import FastMCP

from src.domain.models import MaintenancePriority, WorkOrder

mcp = FastMCP("MaintenanceServices")

APPROVAL_COST_THRESHOLD = 500.0
WORK_ORDERS_DB: dict[str, WorkOrder] = {}

@mcp.tool()
def create_work_order(
    unit_id: str,
    tenant_name: str,
    category: str,
    description: str,
    priority: str,
    estimated_cost: float = 0.0,
) -> dict:
    """
    Log a maintenance work order.
    priority: emergency | high | medium | low
    category: plumbing | electrical | hvac | appliance | general
    """
    try:
        prio = MaintenancePriority(priority.lower())
    except ValueError:
        valid = ", ".join(p.value for p in MaintenancePriority)
        return {"error": f"Invalid priority '{priority}'. Choose from: {valid}."}

    needs_approval = prio == MaintenancePriority.EMERGENCY or estimated_cost > APPROVAL_COST_THRESHOLD

    order = WorkOrder(
        ticket_id=f"WO-{uuid.uuid4().hex[:6].upper()}",
        unit_id=unit_id,
        tenant_name=tenant_name,
        category=category.lower(),
        description=description,
        priority=prio,
        estimated_cost=estimated_cost,
        requires_human_approval=needs_approval,
    )
    WORK_ORDERS_DB[order.ticket_id] = order
    return order.model_dump(mode="json")


@mcp.tool()
def get_work_order_status(ticket_id: str) -> dict:
    """Fetch an existing work order by its ticket ID."""
    order = WORK_ORDERS_DB.get(ticket_id)
    if not order:
        return {"error": f"Work order '{ticket_id}' not found."}
    return order.model_dump(mode="json")