from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message


class ConfigMiddleware(BaseMiddleware):
    """
    Middleware for aiogram bots to inject configuration into the data dictionary
    passed to message handlers.

    This middleware takes a `config` dictionary during initialization and inserts it
    into each event's data dictionary under the key 'config', allowing handlers
    to access configuration settings easily.

    Parameters:
        config (Config): A config class containing configuration settings for the bot.

    Usage:
        Add this middleware to the dispatcher of an aiogram bot to make `config`
        accessible in every handler.
    """

    def __init__(self, config) -> None:
        """
        Initializes the middleware with a configuration dictionary.

        Args:
            config (Config): A configuration class to be injected into message handlers.
        """
        self.config = config

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        """
        Asynchronous call method that gets executed for each incoming update.

        Args:
            handler (Callable[[Message, Dict[str, Any]], Awaitable[Any]]): The next handler in the middleware chain.
            event (Message): The incoming message event from aiogram.
            data (Dict[str, Any]): The data dictionary passed through the handler chain.

        Returns:
            Any: The result of the next handler in the chain.
        """
        data["config"] = self.config
        return await handler(event, data)
