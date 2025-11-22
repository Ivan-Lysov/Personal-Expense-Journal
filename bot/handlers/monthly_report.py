from typing import Any, Dict, List

from ..handler import Handler
from bot.constants import MENU_REPORT, MENU_MAIN
from bot.repo.expenses_repo import monthly_report_by_category


class MonthlyReportHandler(Handler):
    """
    Handle monthly report requests from the main menu.

    This handler reacts to the `MENU_REPORT` callback:
    - Aggregates current month's expenses by category for a given user.
    - Sends a nicely formatted HTML summary with per-category totals
      and a monthly grand total.

    The month is chosen based on the server's current UTC year-month.
    Later this can be extended to accept a specific "YYYY-MM" from user.
    """

    def __init__(self, telegram_client, conn):
        """
        Parameters
        ----------
        telegram_client : Any
            Module or object with a `sendMessage` and \
                `answerCallbackQuery` API.
        conn : sqlite3.Connection
            Open SQLite connection.
        """
        self.tg = telegram_client
        self.conn = conn

    def can_handle(self, update: Dict[str, Any]) -> bool:
        """
        Check if this handler should process the given update.

        It only handles callback queries with data == MENU_REPORT.
        """
        cq = update.get("callback_query")
        if not cq:
            return False
        return cq.get("data") == MENU_REPORT

    def handle(self, update: Dict[str, Any]) -> bool:
        """
        Build and send monthly report grouped by category.

        Returns
        -------
        bool
            False, as the update is fully consumed by this handler.
        """
        cq = update["callback_query"]
        chat_id = cq["message"]["chat"]["id"]
        user_id = cq["from"]["id"]

        rows, total, month_key = monthly_report_by_category(self.conn, user_id)
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
        if not rows:
            text = (
                f"📅 Отчёт за <b>{month_key}</b>\n\n"
                "Пока нет записей за этот месяц."
            )
        else:
            lines: List[str] = []
            lines.append(f"📅 Отчёт за <b>{month_key}</b>\n")
            for r in rows:
                category = r["category"]
                cat_total = float(r["total"])
                lines.append(f"• <b>{category}</b> — {cat_total:.2f}")
            lines.append("")
            lines.append(f"Итого за месяц: <b>{total:.2f}</b>")
            text = "\n".join(lines)
        self.tg.sendMessage(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

        if hasattr(self.tg, "answerCallbackQuery"):
            self.tg.answerCallbackQuery(callback_query_id=cq["id"])

        return False
