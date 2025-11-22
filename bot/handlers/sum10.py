from typing import Any, Dict
from bot.handler import Handler
from bot.constants import MENU_SUM10, MENU_MAIN
from bot.repo.expenses_repo import sum_last_n


class SumLast10Handler(Handler):
    """
    Handle MENU_SUM10 callback: compute sum of last 10 expenses.
    """

    def __init__(self, telegram_client, conn, n: int = 10):
        self.tg = telegram_client
        self.conn = conn
        self.n = n

    def can_handle(self, update: Dict[str, Any]) -> bool:
        if "callback_query" not in update:
            return False
        return update["callback_query"].get("data") == MENU_SUM10

    def handle(self, update: Dict[str, Any]) -> bool:
        cq = update["callback_query"]
        chat_id = cq["message"]["chat"]["id"]
        user_id = cq["from"]["id"]
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "🏠 В главное меню",
                        "callback_data": MENU_MAIN,
                    }
                ],
            ]
        }
        s = sum_last_n(self.conn, user_id, n=self.n)
        body = f"Сумма последних {self.n}: {s:.2f}"
        self.tg.sendMessage(
                chat_id=chat_id,
                text=body,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

        if hasattr(self.tg, "answerCallbackQuery"):
            self.tg.answerCallbackQuery(callback_query_id=cq["id"])
        return False
