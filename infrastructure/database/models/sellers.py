# infrastructure/database/models/sellers.py
import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Integer, Boolean, String, DECIMAL, ForeignKey, TIMESTAMP, text, Enum
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship

from infrastructure.database.models.base import TableNameMixin, Base, TimestampMixin
from infrastructure.database.models.services import Service
from infrastructure.database.models.transactions import Transaction


class SellerStatus(enum.Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    SUSPENDED = 'suspended'
    BANNED = 'banned'

class UserRole(enum.Enum):
    ADMIN = "admin"
    RESELLER = "user"


class Seller(Base, TableNameMixin, TimestampMixin):
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()")
    )
    chat_id: Mapped[int] = mapped_column(BIGINT, unique=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True)
    full_name: Mapped[str] = mapped_column(String)
    user_role: Mapped[str] = mapped_column(Enum(UserRole, name="user_role"))
    debt_limit: Mapped[Decimal] = mapped_column(DECIMAL(precision=16, scale=2))
    current_debt: Mapped[Decimal] = mapped_column(DECIMAL(precision=16, scale=2), default=0, index=True)
    total_profit: Mapped[Decimal] = mapped_column(DECIMAL(precision=16, scale=2), default=0)
    discount_percent: Mapped[Decimal] = mapped_column(DECIMAL(precision=16, scale=2))
    total_services: Mapped[int] = mapped_column(Integer, default=0)
    active_services: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    auto_suspend: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(Enum(SellerStatus, name='seller_status'))

    # Relationships
    services: Mapped[list["Service"]] = relationship(back_populates="seller")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="seller")
    referral_links: Mapped[list["ReferralLink"]] = relationship(back_populates="seller")


class ReferralLink(Base, TableNameMixin, TimestampMixin):
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()")
    )
    created_by: Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    seller_id: Mapped[int] = mapped_column(ForeignKey('sellers.id'))
    code: Mapped[str] = mapped_column(String(50), unique=True, indexed=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), indexed=True)
    max_uses: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, indexed=True)

    # Relationships
    seller: Mapped["Seller"] = relationship(back_populates="referral_links")
