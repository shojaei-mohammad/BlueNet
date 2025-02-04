# infrastructure/database/models/sellers.py
import enum
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Integer, Boolean, String, DECIMAL, text, Enum, false
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship

from infrastructure.database.models.base import TableNameMixin, Base, TimestampMixin

if TYPE_CHECKING:
    from infrastructure.database.models.services import Service
    from infrastructure.database.models.transactions import Transaction
    from infrastructure.database.models.referral_links import ReferralLink


class SellerStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    SUSPENDED = "suspended"
    BANNED = "banned"


class UserRole(enum.Enum):
    ADMIN = "admin"
    RESELLER = "reseller"


class Seller(Base, TableNameMixin, TimestampMixin):
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    chat_id: Mapped[int] = mapped_column(BIGINT, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    full_name: Mapped[str] = mapped_column(String)
    user_role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), server_default=UserRole.RESELLER.name
    )
    debt_limit: Mapped[Decimal] = mapped_column(
        DECIMAL(precision=16, scale=2), nullable=True
    )
    current_debt: Mapped[Decimal] = mapped_column(
        DECIMAL(precision=16, scale=2), server_default="0", index=True
    )
    total_profit: Mapped[Decimal] = mapped_column(
        DECIMAL(precision=16, scale=2), server_default="0"
    )
    discount_percent: Mapped[Decimal] = mapped_column(
        DECIMAL(precision=16, scale=2), server_default="0"
    )
    total_services: Mapped[int] = mapped_column(Integer, server_default="0")
    active_services: Mapped[int] = mapped_column(Integer, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=false(), index=True)
    auto_suspend: Mapped[bool] = mapped_column(Boolean, server_default=false())
    status: Mapped[SellerStatus] = mapped_column(
        Enum(SellerStatus, name="seller_status"),
        server_default=SellerStatus.PENDING.name,
    )

    # Relationships
    services: Mapped[list["Service"]] = relationship(back_populates="seller")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="seller")
    referral_links: Mapped[list["ReferralLink"]] = relationship(back_populates="seller")
