# infrastructure/database/models/routers.py
from typing import Optional

from sqlalchemy import ForeignKey, Enum, String, Integer, Boolean, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship

from infrastructure.database.models.base import TableNameMixin, Base, TimestampMixin
from infrastructure.database.models.services import Service
from infrastructure.database.models.tariffs import ServiceType


class Router(Base, TableNameMixin, TimestampMixin):
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()")
    )
    hostname: Mapped[str] = mapped_column(String(255))
    api_port: Mapped[int] = mapped_column(Integer)
    username: Mapped[str] = mapped_column(String(255))
    password: Mapped[str] = mapped_column(String(255))
    use_ssl: Mapped[bool] = mapped_column(Boolean)
    max_peers: Mapped[int] = mapped_column(Integer)
    current_peers: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    interfaces: Mapped[list["Interface"]] = relationship(back_populates="router")


class Interface(Base, TableNameMixin, TimestampMixin):
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()")
    )
    router_id: Mapped[UUID] = mapped_column(ForeignKey("routers.id"), index=True)
    country_id: Mapped[UUID] = mapped_column(ForeignKey("countries.id"), index=True)
    interface_name: Mapped[str] = mapped_column(String(50))
    public_key: Mapped[str] = mapped_column(String(255))
    listen_port: Mapped[int] = mapped_column(Integer)
    network_subnet: Mapped[str] = mapped_column(String(18))
    service_type: Mapped[str] = mapped_column(
        Enum(ServiceType, name="interface_types"), index=True
    )
    country_code: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    max_peers: Mapped[int] = mapped_column(Integer)
    current_peers: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Relationships
    router: Mapped["Router"] = relationship(back_populates="interfaces")
    services: Mapped[list["Service"]] = relationship(back_populates="interface")
