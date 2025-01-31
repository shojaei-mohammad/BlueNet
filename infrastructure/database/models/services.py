# infrastructure/database/models/services.py
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Enum, TIMESTAMP, Decimal, DECIMAL, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship

from infrastructure.database.models.base import TableNameMixin, Base, TimestampMixin
from infrastructure.database.models.routers import Interface
from infrastructure.database.models.sellers import Seller
from infrastructure.database.models.tariffs import Tariff
from infrastructure.database.models.transactions import Transaction


class ServiceStatus(enum.Enum):
    PENDING = 'pending'
    ACTIVE = 'active'
    EXPIRED = 'expired'
    DELETED = 'deleted'


class Service(Base, TableNameMixin, TimestampMixin):
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()")
    )
    seller_id: Mapped[UUID] = mapped_column(ForeignKey('sellers.id'), index=True)
    tariff_id: Mapped[UUID] = mapped_column(ForeignKey('tariffs.id'))
    interface_id: Mapped[UUID] = mapped_column(ForeignKey('interfaces.id'))
    peer_id: Mapped[UUID] = mapped_column(ForeignKey('peers.id'), index=True)

    purchase_date: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    activation_date: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True, index=True)
    expiry_date: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True, index=True)
    deletion_date: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    status: Mapped[ServiceStatus] = mapped_column(
        Enum(ServiceStatus, name='service_statuses'),
        default=ServiceStatus.PENDING,
        index=True
    )
    original_price: Mapped[Decimal] = mapped_column(DECIMAL(precision=16, scale=2))
    seller_price: Mapped[Decimal] = mapped_column(DECIMAL(precision=16, scale=2))

    # Relationships
    seller: Mapped["Seller"] = relationship(back_populates="services")
    tariff: Mapped["Tariff"] = relationship(back_populates="services")
    interface: Mapped["Interface"] = relationship(back_populates="services")
    peer: Mapped["Peer"] = relationship(back_populates="service", uselist=False)
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="service")


class Peer(Base, TableNameMixin, TimestampMixin):
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()")
    )
    private_key: Mapped[str] = mapped_column(String(255))
    public_key: Mapped[str] = mapped_column(String(255))
    allocated_ip: Mapped[str] = mapped_column(String(15))
    dns_servers: Mapped[str] = mapped_column(String(255))
    qr_code: Mapped[str] = mapped_column(String)
    config_file: Mapped[str] = mapped_column(String)
    peer_comment: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    # Relationships
    service: Mapped["Service"] = relationship(back_populates="peer", uselist=False)