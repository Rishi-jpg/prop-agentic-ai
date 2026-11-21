from datetime import datetime
import uuid
from typing import Optional
from fastmcp import FastMCP

from src.domain.models import PropertyUnit, TourBooking, UnitStatus

mcp = FastMCP("LeasingService")

# In-memory store for local dev...swap for postgres db in production

UNITS_DB: dict[str, PropertyUnit] = {
    "BLDG-A-302": PropertyUnit(
        unit_id="BLDG-A-302",
        building_name="DLF Rose",
        bedrooms=2,
        bathrooms=2.0,
        monthly_rent=2450.0,
        sqft=1050,
        pet_friendly=True,
        couple_friendly=True,
        status=UnitStatus.AVAILABLE,
        available_date="2026-12-01",
    ),
    "BLDG-A-105": PropertyUnit(
        unit_id="BLDG-A-105",
        building_name="DLF Rose",
        bedrooms=1,
        bathrooms=1.0,
        monthly_rent=1800.0,
        sqft=720,
        pet_friendly=False,
        couple_friendly=False,
        status=UnitStatus.AVAILABLE,
        available_date="2026-11-25",
    ),
    "BLDG-B-401": PropertyUnit(
        unit_id="BLDG-B-401",
        building_name="DLF Rose",
        bedrooms=0,
        bathrooms=1.0,
        monthly_rent=1550.0,
        sqft=540,
        pet_friendly=True,
        couple_friendly=True,
        status=UnitStatus.OCCUPIED,
        available_date=None,
    ),
}

TOURS_DB: dict[str, TourBooking] = {}



@mcp.tool()
def search_available_units(
    max_rent: float | None = None,
    min_bedrooms: int | None = None,
    pet_friendly: bool | None = None,
    couple_friendly: bool | None = None,
) -> list[dict]:
    """Search for available rental units based on optional filtering criteria.

    Args:
        max_rent: Maximum monthly rent allowed.
        min_bedrooms: Minimum number of bedrooms required (use 0 for studio).
        pet_friendly: If True, only return units that allow pets.
        couple_friendly: If True, only return units that allow couples.
    """
    matches = []
    for unit in UNITS_DB.values():
        if unit.status != UnitStatus.AVAILABLE:
            continue
        if max_rent is not None and unit.monthly_rent > max_rent:
            continue
        if min_bedrooms is not None and unit.bedrooms < min_bedrooms:
            continue
        if pet_friendly is not None and unit.pet_friendly != pet_friendly:
            continue
        if couple_friendly is not None and unit.couple_friendly != couple_friendly:
            continue
        matches.append(unit.model_dump())
    return matches


@mcp.tool()
def check_income_qualification(unit_id: str, monthly_gross_income: float) -> dict:
    """Verify if a prospect meets the 3x monthly rent income requirement."""
    unit = UNITS_DB.get(unit_id)
    if not unit:
        return {"error": f"Unit '{unit_id}' not found."}

    required = unit.monthly_rent * 3.0
    return {
        "unit_id": unit_id,
        "monthly_rent": unit.monthly_rent,
        "required_monthly_income": required,
        "applicant_monthly_income": monthly_gross_income,
        "qualified": monthly_gross_income >= required,
    }


@mcp.tool()
def book_property_tour(
    unit_id: str,
    prospect_name: str,
    prospect_email: str,
    scheduled_time_iso: str,
) -> dict:
    """Book an in-person tour for an available unit (time in ISO 8601 format)."""
    unit = UNITS_DB.get(unit_id)
    if not unit:
        return {"error": f"Unit '{unit_id}' not found."}
    if unit.status != UnitStatus.AVAILABLE:
        return {"error": f"Unit '{unit_id}' is {unit.status.value} and cannot be toured."}

    try:
        scheduled_dt = datetime.fromisoformat(scheduled_time_iso)
    except ValueError:
        return {"error": "Invalid date format. Use ISO 8601, e.g. '2026-11-25T14:00:00'."}

    booking = TourBooking(
        booking_id=f"TOUR-{uuid.uuid4().hex[:6].upper()}",
        unit_id=unit_id,
        prospect_name=prospect_name,
        prospect_email=prospect_email,
        scheduled_time=scheduled_dt,
    )
    TOURS_DB[booking.booking_id] = booking
    return booking.model_dump(mode="json")


