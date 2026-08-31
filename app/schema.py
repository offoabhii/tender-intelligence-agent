from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal

class Tender(BaseModel):
    title: str = Field(description="Tender title")
    source_url: str
    category: Literal[
        "Charging point operations",
        "Solar",
        "Bus operations (gross cost only)",
        "Bus body building"
    ]
    closing_date: Optional[str] = Field(default="NOT SURE", description="YYYY-MM-DD or NOT SURE")
    issued_by: Optional[str] = Field(default="NOT SURE")
    qualification_criteria: Optional[str] = Field(default="NOT SURE")
    eligibility_status: Optional[str] = Field(default="NOT SURE")
    is_net_cost: bool = Field(default=False, description="True if Net Cost model - MUST BE REJECTED for Bus Ops")
    is_open_now: bool = Field(default=False)
    extraction_confidence: Literal["HIGH", "MEDIUM", "LOW", "NOT SURE"] = "MEDIUM"

    @field_validator("closing_date", "issued_by", "qualification_criteria", "eligibility_status", mode="before")
    @classmethod
    def honest_value(cls, v):
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return "NOT SURE"
        return v