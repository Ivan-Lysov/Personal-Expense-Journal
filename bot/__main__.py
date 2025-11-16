import os
from dotenv import load_dotenv

from bot.dispatcher import Dispatcher
from bot.long_polling import start_long_polling
from bot import telegram_client as tg

from bot.repo.db import get_connection, init_schema
from bot.services.vocab import get_user_categories, get_user_stores
from bot.handlers.start_help import StartHelpHandler
from bot.handlers.menu_callbacks import MenuCallbacksHandler
from bot.handlers.unknown import UnknownCallbackHandler, UnknownTextHandler
from bot.handlers.add_expense_steps import AddExpenseStepsHandler
from bot.handlers.recent import RecentHandler
from bot.handlers.sum10 import SumLast10Handler
from bot.handlers.export_csv import CsvExportHandler
from bot.handlers.monthly_report import MonthlyReportHandler
from bot.handlers.help_menu import HelpMenuHandler


def main():
    """Entry point: env → DB → handlers → long polling."""
    load_dotenv()

    db_path = os.environ.get("DB_PATH", "budget.sqlite3")
    conn = get_connection(db_path)
    init_schema(conn)

    dispatcher = Dispatcher()
    dispatcher.add_handler(StartHelpHandler(tg))
    dispatcher.add_handler(MenuCallbacksHandler(tg, conn, get_user_categories))
    dispatcher.add_handler(AddExpenseStepsHandler(tg,
                                                  conn, get_user_categories,
                                                  get_user_stores))
    dispatcher.add_handler(RecentHandler(tg, conn, n=10))
    dispatcher.add_handler(SumLast10Handler(tg, conn, n=10))
    dispatcher.add_handler(MonthlyReportHandler(tg, conn))
    dispatcher.add_handler(CsvExportHandler(tg, conn))
    dispatcher.add_handler(HelpMenuHandler(tg))
    dispatcher.add_handler(UnknownCallbackHandler(tg))
    dispatcher.add_handler(UnknownTextHandler(tg))

    start_long_polling(dispatcher)


if __name__ == "__main__":
    main()
