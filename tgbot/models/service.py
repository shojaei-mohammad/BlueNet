from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PurchaseData(BaseModel):
    user_id: str = Field(
        ..., description="Unique ID of the user purchasing the service."
    )
    email: str = Field(..., description="Email of the user.")
    duration_days: int = Field(..., description="Duration of the service in days.")
    interface_name: str = Field(
        default="wireguard1", description="Name of the WireGuard interface."
    )
    comment: Optional[str] = Field(
        default=None, description="Optional comment for the peer."
    )
    seller_id: int = Field(..., description="ID of the seller.")
    purchase_id: UUID = Field(..., description="Unique ID of the purchase.")
