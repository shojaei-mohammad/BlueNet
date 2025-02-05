# infrastructure/database/models/transactions.py
import enum
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, DECIMAL, String, Enum, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship

from infrastructure.database.models.base import TableNameMixin, Base, TimestampMixin

if TYPE_CHECKING:
    from infrastructure.database.models.sellers import Seller
    from infrastructure.database.models.services import Service


class TransactionType(enum.Enum):
    PURCHASE = "purchase"
    SETTLEMENT = "settlement"


class Transaction(Base, TableNameMixin, TimestampMixin):
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), index=True)
    service_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("services.id"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(DECIMAL(precision=16, scale=2))
    transaction_type: Mapped[str] = mapped_column(
        Enum(TransactionType, name="transaction_types"), index=True
    )
    description: Mapped[str] = mapped_column(String(255))

    # Relationships
    seller: Mapped["Seller"] = relationship(back_populates="transactions")
    service: Mapped[Optional["Service"]] = relationship(back_populates="transactions")
