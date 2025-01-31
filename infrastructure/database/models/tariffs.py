# infrastructure/database/models/tariffs.py
import enum
from typing import Optional

from sqlalchemy import String, Enum, Integer, Decimal, DECIMAL, Boolean, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship

from infrastructure.database.models.base import TableNameMixin, Base, TimestampMixin
from infrastructure.database.models.routers import Interface
from infrastructure.database.models.services import Service


class ServiceType(enum.Enum):
    DYNAMIC = "dynamic"
    FIXED = "fixed"


class Tariff(Base, TableNameMixin, TimestampMixin):
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()")
    )
    service_type: Mapped[str] = mapped_column(
        Enum(ServiceType, name="service_types")
    )
    country_code: Mapped[Optional[str]] = mapped_column(
        ForeignKey("countries.code"),
        String(2),
        nullable=True
    )
    duration_days: Mapped[int] = mapped_column(Integer)
    price: Mapped[Decimal] = mapped_column(DECIMAL(precision=16, scale=2))
    description: Mapped[str] = mapped_column(String(255))

    # Relationships
    services: Mapped[list["Service"]] = relationship(back_populates="tariff")
    country: Mapped["Country"] = relationship(back_populates="tariffs")


class Country(Base, TableNameMixin, TimestampMixin):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(2), unique=True)  # ISO 3166-1 alpha-2
    name: Mapped[str] = mapped_column(String(100))
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    tariffs: Mapped[list["Tariff"]] = relationship(back_populates="country")
    interfaces: Mapped[list["Interface"]] = relationship(back_populates="country")
