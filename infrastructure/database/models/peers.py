# infrastructure/database/models/peers.py
from typing import TYPE_CHECKING

from sqlalchemy import String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship

from infrastructure.database.models.base import TableNameMixin, Base, TimestampMixin

if TYPE_CHECKING:
    from infrastructure.database.models.services import Service


class Peer(Base, TableNameMixin, TimestampMixin):
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    public_id: Mapped[str] = mapped_column(String, index=True)
    private_key: Mapped[str] = mapped_column(String(255))
    public_key: Mapped[str] = mapped_column(String(255))
    allocated_ip: Mapped[str] = mapped_column(String(15))
    dns_servers: Mapped[str] = mapped_column(String(255))
    end_point: Mapped[str] = mapped_column(String)
    config_file: Mapped[str] = mapped_column(String)
    peer_comment: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    # Relationships
    service: Mapped["Service"] = relationship(
        "Service", back_populates="peer", uselist=False
    )
