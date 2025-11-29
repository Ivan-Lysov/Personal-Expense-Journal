from typing import Any, Dict

from bot.constants import (
    MENU_ADD,
    MENU_EXPORT_CSV,
    MENU_HELP,
    MENU_MAIN,
    MENU_RECENT,
    MENU_REPORT,
    MENU_SUM10,
    STATE_ASK_CATEGORY,
)
from bot.services.keyboards import main_menu_keyboard

from ..handler import Handler
from ..repo.state_repo import set_state


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

        if data in {MENU_ADD, MENU_RECENT, MENU_SUM10, MENU_REPORT, MENU_EXPORT_CSV, MENU_HELP, MENU_MAIN}:
            self._delete_menu_message(cq)

        if data == MENU_ADD:
            # Transition to ASK_CATEGORY (payload may contain last_msg_id)
            categories = self.get_user_categories(self.conn, user_id)
            keyboard = {
                "inline_keyboard": [
                    *([{"text": name, "callback_data": f"CATEGORY::{name}"}] for name in categories),
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
            keyboard = main_menu_keyboard()
            self.tg.sendMessage(
                chat_id=chat_id,
                text="Главное меню:",
                reply_markup=keyboard,
            )
            if hasattr(self.tg, "answerCallbackQuery"):
                self.tg.answerCallbackQuery(callback_query_id=cq["id"])
            return False

        return True

    def _delete_menu_message(self, cq: Dict[str, Any]) -> None:
        """
        Delete the message that contained the pressed main-menu button.

        Parameters
        ----------
        cq : dict
            Telegram callback_query object.
        """
        msg = cq.get("message") or {}
        chat = msg.get("chat") or {}
        chat_id = chat.get("id")
        msg_id = msg.get("message_id")

        if chat_id is None or msg_id is None:
            return

        try:
            self.tg.deleteMessage(chat_id=chat_id, message_id=msg_id)
        except Exception:
            pass
