from ..handler import Handler
from bot.constants import MENU_ADD, STATE_ASK_CATEGORY, MENU_MAIN, MENU_HELP, MENU_RECENT, MENU_SUM10, \
      MENU_REPORT, MENU_EXPORT_CSV
from ..repo.state_repo import set_state
from typing import Any


class MenuCallbacksHandler(Handler):
    """
    Route top-level inline menu callback queries.

    For MVP we implement only MENU_ADD:
    - set FSM to ASK_CATEGORY
    - render category buttons + "New category" + "Cancel"
    """

    def __init__(self, telegram_client, conn, categories_provider):
        """
        Parameters
        ----------
        telegram_client : Any
            Your thin HTTP client for Telegram Bot API.
        conn : sqlite3.Connection
            Open SQLite connection.
        categories_provider : Callable[[sqlite3.Connection, int], list[str]]
            Function to fetch merged (defaults ∪ used) categories for a user.
        """
        self.tg = telegram_client
        self.conn = conn
        self.get_user_categories = categories_provider

    def can_handle(self, update: dict) -> bool:
        cq = update.get("callback_query")
        if not cq:
            return False
        data = cq.get("data", "")
        return data in {
            MENU_ADD,
            MENU_RECENT,
            MENU_SUM10,
            MENU_REPORT,
            MENU_EXPORT_CSV,
            MENU_HELP,
            MENU_MAIN,
        }

    def handle(self, update: dict) -> bool:
        cq = update["callback_query"]
        data = cq.get("data", "")
        chat_id = cq["message"]["chat"]["id"]
        user_id = cq["from"]["id"]

        if data == MENU_ADD:
            # Transition to ASK_CATEGORY (payload may contain last_msg_id)
            categories = self.get_user_categories(self.conn, user_id)
            keyboard = {
                "inline_keyboard": [
                    *(
                        [
                            {"text": name, "callback_data": f"CATEGORY::{name}"}
                        ]
                        for name in categories
                    ),
                    [{"text": "➕ Новая категория", "callback_data": "CATEGORY::NEW"}],
                    [{"text": "❌ Отмена", "callback_data": "CANCEL"}],
                ]
            }

            msg = self.tg.sendMessage(
                chat_id=chat_id,
                text="Выберите категорию:",
                reply_markup=keyboard,
            )

            try:
                last_id = int(msg.get("message_id"))
            except Exception:
                last_id = None

            payload: dict[str, Any] = {}
            if last_id is not None:
                payload["last_msg_id"] = last_id

            set_state(self.conn, user_id, STATE_ASK_CATEGORY, payload)

            if hasattr(self.tg, "answerCallbackQuery"):
                self.tg.answerCallbackQuery(callback_query_id=cq["id"])
            return False

        if data == MENU_MAIN:
            keyboard = {
                "inline_keyboard": [
                    [{"text": "➕ Добавить расход",    "callback_data": MENU_ADD}],
                    [{"text": "🧾 Последние записи",  "callback_data": MENU_RECENT}],
                    [{"text": "➗ Сумма последних 10", "callback_data": MENU_SUM10}],
                    [{"text": "📅 Отчёт за месяц",    "callback_data": MENU_REPORT}],
                    [{"text": "⬇️ Экспорт CSV",       "callback_data": MENU_EXPORT_CSV}],
                    [{"text": "ℹ️ Справка",           "callback_data": MENU_HELP}],
                ]
            }
            self.tg.sendMessage(
                chat_id=chat_id,
                text="Главное меню:",
                reply_markup=keyboard,
            )
            if hasattr(self.tg, "answerCallbackQuery"):
                self.tg.answerCallbackQuery(callback_query_id=cq["id"])
            return False

        return True
