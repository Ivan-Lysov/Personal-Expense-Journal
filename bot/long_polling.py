# bot/long_polling.py
from typing import Any, Dict, List
import logging

import bot.telegram_client as tg

logger = logging.getLogger("expense_bot.long_polling")


def start_long_polling(dispatcher) -> None:
    """
    Long-polling loop: fetch updates from Telegram and pass them to dispatcher.

    Parameters
    ----------
    dispatcher : Dispatcher
        Central dispatcher for incoming updates.
    """
    logger.info("Entering long-polling loop")

    next_update_offset: int | None = None

    while True:
        try:
            updates: List[Dict[str, Any]] = tg.getUpdates(
                offset=next_update_offset,
                timeout=25,
            )
        except Exception as exc:
            logger.exception("getUpdates failed: %r", exc)
            continue

        if not updates:
            continue

        for update in updates:
            update_id = update.get("update_id")
            logger.debug("Received update_id=%s", update_id)

            try:
                dispatcher.dispatch(update)
            except Exception as exc:
                logger.exception(
                    "Error while handling update_id=%s: %r", update_id, exc
                )

            if update_id is not None:
                next_update_offset = update_id + 1
