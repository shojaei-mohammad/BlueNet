from datetime import datetime

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models, providing ORM capabilities."""

    pass


class TableNameMixin:
    """
    Mixin to provide a standard table name generation based on the class name.
    This generates table names by converting the class name to lowercase and appending 's'.
    """

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower() + "s"


class TimestampMixin:
    """
    Mixin to add timestamp columns 'CreatedAt' and 'UpdatedAt' to a SQLAlchemy model.
    'CreatedAt' is set when the record is first created and 'UpdatedAt' is updated
    every time the record is modified.
    """

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
