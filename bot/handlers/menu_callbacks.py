from ..handler import Handler
from bot.constants import MENU_ADD, STATE_ASK_CATEGORY
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
        return "callback_query" in update

    def handle(self, update: dict) -> bool:
        cq = update["callback_query"]
        data = cq.get("data", "")
        chat_id = cq["message"]["chat"]["id"]
        user_id = cq["from"]["id"]

        if data == MENU_ADD:
            # Transition to ASK_CATEGORY (payload is empty for now)
            set_state(self.conn, user_id, STATE_ASK_CATEGORY, payload={})

            categories = self.get_user_categories(self.conn, user_id)
            keyboard = {
                "inline_keyboard": [
                    *[[{"text": name, "callback_data": f"CATEGORY::{name}"}] for name in categories],
                    [{"text": "➕ Новая категория", "callback_data": "CATEGORY::NEW"}],
                    [{"text": "❌ Отмена", "callback_data": "CANCEL"}],
                ]
            }
            self.tg.sendMessage(chat_id=chat_id, text="Выберите категорию:", reply_markup=keyboard)

            if hasattr(self.tg, "answerCallbackQuery"):
                self.tg.answerCallbackQuery(callback_query_id=cq["id"])
            return False

        return True
