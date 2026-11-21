import json
import pytest
from fastmcp import Client

from src.mcp_servers.leasing_server import mcp as leasing_mcp
from src.mcp_servers.maintenance_server import mcp as maintenance_mcp


@pytest.mark.asyncio
async def test_leasing_mcp_workflow():
    async with Client(leasing_mcp) as client:
        tools = await client.list_tools()
        names = {t.name for t in tools}
        assert {"search_available_units", "check_income_qualification", "book_property_tour"} <= names

        # Search pet- and couple-friendly units under $2500
        search_res = await client.call_tool(
            "search_available_units",
            {"max_rent": 2500.0, "pet_friendly": True, "couple_friendly": True},
        )
        units = json.loads(search_res.content[0].text)
        assert len(units) == 1
        assert units[0]["unit_id"] == "BLDG-A-302"

        # Verify 3x income rule ($2450 * 3 = $7350)
        qual_res = await client.call_tool(
            "check_income_qualification",
            {"unit_id": "BLDG-A-302", "monthly_gross_income": 8000.0},
        )
        assert json.loads(qual_res.content[0].text)["qualified"] is True


@pytest.mark.asyncio
async def test_maintenance_mcp_approval_flag():
    async with Client(maintenance_mcp) as client:
        res = await client.call_tool(
            "create_work_order",
            {
                "unit_id": "BLDG-A-302",
                "tenant_name": "Jordan Lee",
                "category": "plumbing",
                "description": "Burst pipe under kitchen sink",
                "priority": "emergency",
                "estimated_cost": 650.0,
            },
        )
        order = json.loads(res.content[0].text)
        assert order["ticket_id"].startswith("WO-")
        assert order["requires_human_approval"] is True