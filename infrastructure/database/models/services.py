# infrastructure/database/models/services.py
import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Enum, TIMESTAMP, DECIMAL, text, String, BIGINT
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship

from infrastructure.database.models.base import TableNameMixin, Base, TimestampMixin

if TYPE_CHECKING:
    from infrastructure.database.models.sellers import Seller
    from infrastructure.database.models.tariffs import Tariff
    from infrastructure.database.models.interfaces import Interface
    from infrastructure.database.models.peers import Peer
    from infrastructure.database.models.transactions import Transaction


class ServiceStatus(enum.Enum):
    UNUSED = "unused"
    INACTIVE = "inactive"
    ACTIVE = "active"
    EXPIRED = "expired"
    DELETED = "deleted"


class Service(Base, TableNameMixin, TimestampMixin):
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), index=True)
    tariff_id: Mapped[UUID] = mapped_column(ForeignKey("tariffs.id"))
    interface_id: Mapped[UUID] = mapped_column(ForeignKey("interfaces.id"))
    peer_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("peers.id"), index=True, nullable=True
    )

    purchase_date: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    activation_date: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, index=True
    )
    expiry_date: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, index=True
    )
    deletion_date: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    status: Mapped[ServiceStatus] = mapped_column(
        Enum(ServiceStatus, name="service_statuses"),
        server_default=ServiceStatus.INACTIVE.name,
        index=True,
    )
    original_price: Mapped[Decimal] = mapped_column(DECIMAL(precision=16, scale=2))
    seller_price: Mapped[Decimal] = mapped_column(DECIMAL(precision=16, scale=2))
    total_bytes: Mapped[Optional[int]] = mapped_column(
        BIGINT, server_default="0", nullable=True
    )
    download_bytes: Mapped[Optional[int]] = mapped_column(
        BIGINT, server_default="0", nullable=True
    )
    upload_bytes: Mapped[Optional[int]] = mapped_column(
        BIGINT, server_default="0", nullable=True
    )
    last_handshake: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    custom_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Relationships
    seller: Mapped["Seller"] = relationship("Seller", back_populates="services")
    tariff: Mapped["Tariff"] = relationship("Tariff", back_populates="services")
    interface: Mapped["Interface"] = relationship(
        "Interface", back_populates="services"
    )
    peer: Mapped["Peer"] = relationship("Peer", back_populates="service", uselist=False)
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="service"
    )
