from typing import Optional

from sqlalchemy import Integer, BigInteger, String
from sqlalchemy.orm import mapped_column, Mapped
from typing_extensions import Annotated

from .base import TimestampMixin, TableNameMixin, Base

str_255 = Annotated[str, mapped_column(String(255), nullable=True)]


class BotUser(Base, TimestampMixin, TableNameMixin):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ChatID: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True, unique=True
    )
    Name: Mapped[Optional[str_255]]
    Lastname: Mapped[Optional[str_255]]
    Username: Mapped[Optional[str_255]]
    ReferralCode: Mapped[int] = mapped_column(BigInteger, nullable=True)
    ReferredBy: Mapped[int] = mapped_column(BigInteger, nullable=True)
    ReferralCount: Mapped[int] = mapped_column(Integer, default=0)
    ReferralLink: Mapped[str_255]
    PrefLanguage: Mapped[str_255]

    def __repr__(self):
        return f"<User {self.id} {self.ChatID} {self.Username}>"
