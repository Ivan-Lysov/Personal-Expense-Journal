from typing import Any, Dict, List
from bot.handler import Handler
from bot.constants import MENU_RECENT
from bot.repo.expenses_repo import select_last_n


class RecentHandler(Handler):
    """
    Handle MENU_RECENT callback: show last 10 expenses.

    Notes
    -----
    - Minimal plain text list. Later we can add pagination ("More") if needed.
    """

    def __init__(self, telegram_client, conn, n: int = 10):
        self.tg = telegram_client
        self.conn = conn
        self.n = n

    def can_handle(self, update: Dict[str, Any]) -> bool:
        if "callback_query" not in update:
            return False
        return update["callback_query"].get("data") == MENU_RECENT

    def handle(self, update: Dict[str, Any]) -> bool:
        cq = update["callback_query"]
        chat_id = cq["message"]["chat"]["id"]
        user_id = cq["from"]["id"]

        rows = select_last_n(self.conn, user_id, n=self.n, offset=0)
        if not rows:
            self.tg.sendMessage(chat_id=chat_id, text="Пока нет записей.")
        else:
            lines: List[str] = []
            for r in rows:
                # created_at is UTC ISO-8601, we just show as-is
                lines.append(
                    f"{r['created_at']} — {r['category']} @ {r['store']} : {r['amount']}"
                    + (f" — {r['note']}" if r['note'] else "")
                )
            body = "Последние записи:\n" + "\n".join(lines)
            self.tg.sendMessage(chat_id=chat_id, text=body)

        if hasattr(self.tg, "answerCallbackQuery"):
            self.tg.answerCallbackQuery(callback_query_id=cq["id"])
        return False
