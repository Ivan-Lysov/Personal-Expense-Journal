# bot/dispatcher.py
from typing import List, Dict, Any
import logging

from bot.handler import Handler

logger = logging.getLogger("expense_bot.dispatcher")


class Dispatcher:
    """
    Simple dispatcher that routes updates to registered handlers.
    """

    def __init__(self) -> None:
        self.handlers: List[Handler] = []

    def add_handler(self, handler: Handler) -> None:
        """
        Register a new handler.

        Parameters
        ----------
        handler : Handler
            Handler instance to register.
        """
        self.handlers.append(handler)
        logger.debug("Handler registered: %s", handler.__class__.__name__)

    def dispatch(self, update: Dict[str, Any]) -> None:
        """
        Pass update through handlers chain until one fully consumes it.

        Parameters
        ----------
        update : dict
            Raw Telegram update.
        """
        for handler in self.handlers:
            if not handler.can_handle(update):
                continue

            name = handler.__class__.__name__
            logger.debug("Update routed to handler: %s", name)

            consumed = handler.handle(update)
            logger.debug("Handler %s consumed=%s", name, consumed)

            if consumed is False:
                break
