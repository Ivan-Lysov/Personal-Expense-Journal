# bot/__main__.py
import os
from dotenv import load_dotenv

from bot.dispatcher import Dispatcher
from bot.long_polling import start_long_polling
from bot import telegram_client as tg  # модуль, не класс!

from bot.repo.db import get_connection, init_schema
from bot.services.vocab import get_user_categories
from bot.handlers.start_help import StartHelpHandler
from bot.handlers.menu_callbacks import MenuCallbacksHandler
from bot.handlers.unknown import UnknownCallbackHandler, UnknownTextHandler

def main():
    """Entry point: env → DB → handlers → long polling."""
    load_dotenv()

    db_path = os.environ.get("DB_PATH", "budget.sqlite3")
    conn = get_connection(db_path)
    init_schema(conn)

    dispatcher = Dispatcher()
    dispatcher.add_handler(StartHelpHandler(tg))
    dispatcher.add_handler(MenuCallbacksHandler(tg, conn, get_user_categories))
    dispatcher.add_handler(UnknownCallbackHandler(tg))
    dispatcher.add_handler(UnknownTextHandler(tg))

    start_long_polling(dispatcher)

if __name__ == "__main__":
    main()
