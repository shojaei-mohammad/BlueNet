# infrastructure/database/models/routers.py
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, Boolean, text, true, false
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship

from infrastructure.database.models.base import TableNameMixin, Base, TimestampMixin

if TYPE_CHECKING:
    from infrastructure.database.models.interfaces import Interface


class Router(Base, TableNameMixin, TimestampMixin):
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    hostname: Mapped[str] = mapped_column(String(255))
    api_port: Mapped[int] = mapped_column(Integer)
    username: Mapped[str] = mapped_column(String(255))
    password: Mapped[str] = mapped_column(String(255))
    use_ssl: Mapped[bool] = mapped_column(Boolean, server_default=false())
    max_peers: Mapped[int] = mapped_column(Integer)
    current_peers: Mapped[int] = mapped_column(Integer, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true())

    # Relationships
    interfaces: Mapped[list["Interface"]] = relationship("Interface", back_populates="router")
