# infrastructure/database/models/tariffs.py
import enum
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Enum, Integer, DECIMAL, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship

from infrastructure.database.models.base import TableNameMixin, Base, TimestampMixin

if TYPE_CHECKING:
    from infrastructure.database.models.services import Service
    from infrastructure.database.models.countries import Country


class ServiceType(enum.Enum):
    DYNAMIC = "dynamic"
    FIXED = "fixed"


class Tariff(Base, TableNameMixin, TimestampMixin):
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    service_type: Mapped[str] = mapped_column(Enum(ServiceType, name="service_types"))
    country_code: Mapped[Optional[str]] = mapped_column(
        String(2), ForeignKey("countries.code"), nullable=True
    )
    duration_days: Mapped[int] = mapped_column(Integer)
    price: Mapped[Decimal] = mapped_column(DECIMAL(precision=16, scale=2))
    description: Mapped[str] = mapped_column(String(255))

    # Relationships
    services: Mapped[list["Service"]] = relationship("Service", back_populates="tariff")
    country: Mapped["Country"] = relationship("Country", back_populates="tariffs")
