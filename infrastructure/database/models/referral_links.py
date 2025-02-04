# infrastructure/database/models/referral_links.py
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, Integer, Boolean, TIMESTAMP, text, true
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship

from infrastructure.database.models.base import TableNameMixin, Base

if TYPE_CHECKING:
    from infrastructure.database.models.sellers import Seller


class ReferralLink(Base, TableNameMixin):
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    created_by: Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    seller_id: Mapped[UUID] = mapped_column(ForeignKey("sellers.id"))
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), index=True
    )
    max_uses: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    used_count: Mapped[int] = mapped_column(Integer, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true(), index=True)

    # Relationships
    seller: Mapped["Seller"] = relationship(back_populates="referral_links")
