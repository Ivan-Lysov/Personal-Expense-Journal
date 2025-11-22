
import logging
import os

from dotenv import load_dotenv

from bot.repo.db import get_connection, init_schema
from bot.dispatcher import Dispatcher
from bot.long_polling import start_long_polling
import bot.telegram_client as tg

from bot.services.vocab import get_user_categories, get_user_stores

from bot.handlers.start_help import StartHelpHandler
from bot.handlers.menu_callbacks import MenuCallbacksHandler
from bot.handlers.add_expense_steps import AddExpenseStepsHandler
from bot.handlers.recent import RecentHandler
from bot.handlers.sum10 import SumLast10Handler
from bot.handlers.monthly_report import MonthlyReportHandler
from bot.handlers.export_csv import CsvExportHandler
from bot.handlers.help_menu import HelpMenuHandler
from bot.handlers.unknown import UnknownCallbackHandler, UnknownTextHandler


def setup_logging() -> logging.Logger:
    """
    Configure root logger for the bot.

    Uses single env variable LOG_LEVEL: DEBUG, INFO, WARNING, ERROR, CRITICAL.

    Returns
    -------
    logging.Logger
        Configured logger instance for the bot.
    """
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger("expense_bot")


def main() -> None:
    """Entry point: env → DB → handlers → long polling."""
    logger = setup_logging()
    load_dotenv()

    db_path = os.environ.get("DB_PATH", "budget.sqlite3")
    conn = get_connection(db_path)
    init_schema(conn)

    dispatcher = Dispatcher()
    dispatcher.add_handler(StartHelpHandler(tg))
    dispatcher.add_handler(MenuCallbacksHandler(tg, conn, get_user_categories))
    dispatcher.add_handler(
        AddExpenseStepsHandler(tg, conn, get_user_categories, get_user_stores)
    )
    dispatcher.add_handler(RecentHandler(tg, conn, n=10))
    dispatcher.add_handler(SumLast10Handler(tg, conn, n=10))
    dispatcher.add_handler(MonthlyReportHandler(tg, conn))
    dispatcher.add_handler(CsvExportHandler(tg, conn))
    dispatcher.add_handler(HelpMenuHandler(tg))
    dispatcher.add_handler(UnknownCallbackHandler(tg))
    dispatcher.add_handler(UnknownTextHandler(tg))

    logger.info("Bot initialized, starting long polling loop")
    start_long_polling(dispatcher)


if __name__ == "__main__":
    main()