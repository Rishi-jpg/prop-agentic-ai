import pytest
from src.domain.models import PropertyUnit, UnitStatus
from src.llm.base import Message
from src.llm.mock_provider import MockLLMProvider


@pytest.mark.asyncio
async def test_domain_and_provider_contract():
    unit = PropertyUnit(
        unit_id="BLDG-A-302",
        building_name="Oakridge Apartments",
        bedrooms=2,
        bathrooms=2.0,
        monthly_rent=2450.0,
        sqft=1050,
        status=UnitStatus.AVAILABLE,
    )
    assert unit.unit_id == "BLDG-A-302"

    provider = MockLLMProvider()
    resp = await provider.generate(
        messages=[Message(role="user", content="Is unit BLDG-A-302 available?")],
        system_prompt="You are a leasing assistant.",
    )
    assert "BLDG-A-302" in resp.content
    assert len(provider.call_history) == 1