import logging
from decimal import Decimal
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from infrastructure.database.repo.requests import RequestsRepo


class DatabaseMiddleware(BaseMiddleware):
    def __init__(
        self,
        session_pool: async_sessionmaker,
        default_debt_limit: Decimal = Decimal("0.00"),
        default_discount: Decimal = Decimal("0.00"),
    ) -> None:
        """
        Initialize the database middleware.

        Args:
            session_pool: SQLAlchemy async session maker
            default_debt_limit: Default debt limit for new sellers
            default_discount: Default discount percentage for new sellers
        """
        self.session_pool = session_pool
        self.default_debt_limit = default_debt_limit
        self.default_discount = default_discount

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        if not event.from_user:
            return await handler(event, data)

        async with self.session_pool() as session:
            repo = RequestsRepo(session)

            # Get or create seller with basic information
            try:
                seller = await repo.sellers.get_or_create_seller(
                    chat_id=event.from_user.id,
                    username=event.from_user.username or f"user_{event.from_user.id}",
                    full_name=event.from_user.full_name,
                )

                data["session"] = session
                data["repo"] = repo
                data["seller"] = seller  # Changed from "user" to "seller"
                result = await handler(event, data)

                return result

            except Exception as e:
                # Log the error but allow the handler to proceed
                logging.error(f"Failed to create/update seller in middleware: {e}")
                data["session"] = session
                data["repo"] = repo
                data["seller"] = None
                return await handler(event, data)
