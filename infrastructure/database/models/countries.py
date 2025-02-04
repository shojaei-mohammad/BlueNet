# infrastructure/database/models/countries.py
from typing import TYPE_CHECKING

from sqlalchemy import String, Boolean, text, true
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship

from infrastructure.database.models.base import TableNameMixin, Base, TimestampMixin

if TYPE_CHECKING:
    from infrastructure.database.models.tariffs import Tariff
    from infrastructure.database.models.interfaces import Interface


class Country(Base, TableNameMixin, TimestampMixin):
    __tablename__ = "countries"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    code: Mapped[str] = mapped_column(String(2), unique=True)  # ISO 3166-1 alpha-2
    name: Mapped[str] = mapped_column(String(100))
    is_available: Mapped[bool] = mapped_column(Boolean, server_default=true())

    # Relationships
    tariffs: Mapped[list["Tariff"]] = relationship(back_populates="country")
    interfaces: Mapped[list["Interface"]] = relationship(back_populates="country")
