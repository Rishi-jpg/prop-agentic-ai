from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, PositiveFloat, PositiveInt

class UnitStatus(str, Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"
    RESERVED = "reserved"

class MaintenancePriority(str, Enum):
    EMERGENCY = "emergency"  # Active leak, no heat/AC, gas smell, broken lock
    HIGH = "high"            # Broken fridge, clogged only toilet
    MEDIUM = "medium"        # Dishwasher issue, minor leak
    LOW = "low"              # Squeaky door, paint touch-up

class PropertyUnit(BaseModel):
    unit_id: str = Field(..., description="Unique unit identifier, e.g., 'BLDG-A-302'")
    building_name: str = Field(..., description="Name of the apartment complex")
    bedrooms: int = Field(..., ge=0, description="0 for studio, 1+ for bedrooms")
    bathrooms: PositiveFloat
    monthly_rent: PositiveFloat = Field(..., description="Monthly rent in India")
    sqft: PositiveInt
    pet_friendly: bool = True
    couple_friendly: bool = Field(True, description="Whether unmarried or married couples are permitted")
    status: UnitStatus = UnitStatus.AVAILABLE
    available_date: Optional[str] = Field(None, description="ISO date YYYY-MM-DD")

class TourBooking(BaseModel):
    booking_id: str
    unit_id: str
    prospect_name: str
    prospect_email: str
    scheduled_time: datetime = Field(..., description="ISO 8601 datetime for the tour")
    status: str = "confirmed"


class WorkOrder(BaseModel):
    ticket_id: str
    unit_id: str
    tenant_name: str
    category: str = Field(..., description="plumbing, electrical, hvac, appliance, general")
    description: str
    priority: MaintenancePriority
    estimated_cost: float = Field(0.0, ge=0.0, description="Estimated vendor cost in USD")
    requires_human_approval: bool = Field(
        False,
        description="True if emergency dispatch or estimated_cost > $500"
    )