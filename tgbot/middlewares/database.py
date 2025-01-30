from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from infrastructure.database.repo.requests import RequestsRepo


class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, session_pool: async_sessionmaker) -> None:
        self.session_pool = session_pool

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        async with self.session_pool() as session:
            repo = RequestsRepo(session)

            # Retrieve or create a user using the new BotUser model structure
            user = await repo.users.get_or_create_user(
                chat_id=event.from_user.id,
                name=event.from_user.first_name,
                last_name=event.from_user.last_name,
                username=event.from_user.username,
                pref_language=event.from_user.language_code,
            )

            data["session"] = session
            data["repo"] = repo
            data["user"] = user
            result = await handler(event, data)
        return result
