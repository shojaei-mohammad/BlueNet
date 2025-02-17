# infrastructure/database/models/interfaces.py
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Enum, String, Integer, Boolean, text, true
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship

from infrastructure.database.models.base import TableNameMixin, Base, TimestampMixin
from infrastructure.database.models.tariffs import ServiceType

if TYPE_CHECKING:
    from infrastructure.database.models.routers import Router
    from infrastructure.database.models.services import Service
    from infrastructure.database.models.countries import Country


class Interface(Base, TableNameMixin, TimestampMixin):
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    router_id: Mapped[UUID] = mapped_column(ForeignKey("routers.id"), index=True)
    country_id: Mapped[UUID] = mapped_column(ForeignKey("countries.id"), index=True)
    interface_name: Mapped[str] = mapped_column(String(50))
    public_key: Mapped[str] = mapped_column(String(255))
    dns_servers: Mapped[str] = mapped_column(String, server_default="1.1.1.1,8.8.8.8")
    allowed_ips: Mapped[str] = mapped_column(String, server_default="0.0.0.0/0, ::/0")
    endpoint: Mapped[str] = mapped_column(String)
    network_subnet: Mapped[str] = mapped_column(String(18))
    service_type: Mapped[str] = mapped_column(
        Enum(ServiceType, name="interface_types"), index=True
    )
    country_code: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    max_peers: Mapped[int] = mapped_column(Integer)
    current_peers: Mapped[int] = mapped_column(Integer, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true(), index=True)

    # Relationships
    router: Mapped["Router"] = relationship("Router", back_populates="interfaces")
    country: Mapped["Country"] = relationship("Country", back_populates="interfaces")
    services: Mapped[list["Service"]] = relationship(
        "Service", back_populates="interface"
    )
