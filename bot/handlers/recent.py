import logging
import sqlite3
from typing import Any, Dict, List

from bot.constants import MENU_ADD, MENU_MAIN, MENU_RECENT
from bot.handler import Handler

logger = logging.getLogger("expense_bot.recent")


class RecentHandler(Handler):
    """
    Show recent expenses for the user with simple pagination.

    Logic
    -----
    • Handles MENU_RECENT (first page, offset=0).
    • Handles "RECENT_MORE::<offset>" for next pages.
    • Each page shows up to `n` records, ordered by created_at DESC.
    • If there are potentially more records, shows "Показать ещё" button.
    • Footer always has:
        - "➕ Добавить расход"
        - "🏠 В главное меню"
    """

    def __init__(self, telegram_client: Any, conn: sqlite3.Connection, n: int = 10) -> None:
        """
        Parameters
        ----------
        telegram_client : Any
            Thin Telegram client module (sendMessage, answerCallbackQuery, ...).
        conn : sqlite3.Connection
            Open SQLite connection.
        n : int, optional
            Page size (number of records per page), by default 10.
        """
        self.tg = telegram_client
        self.conn = conn
        self.n = n

    def can_handle(self, update: Dict[str, Any]) -> bool:
        """
        Handle only callback_query with MENU_RECENT or RECENT_MORE::<offset>.
        """
        cq = update.get("callback_query")
        if not cq:
            return False
        data = cq.get("data", "")
        return data == MENU_RECENT or data.startswith("RECENT_MORE::")

    def handle(self, update: Dict[str, Any]) -> bool:
        """
        Render one page of recent expenses.

        Returns
        -------
        bool
            False, as this handler fully consumes the update.
        """
        cq = update["callback_query"]
        chat_id = cq["message"]["chat"]["id"]
        user_id = cq["from"]["id"]
        data = cq.get("data", "")

        if data == MENU_RECENT:
            offset = 0
        else:
            try:
                self.tg.deleteMessage(
                    chat_id=chat_id,
                    message_id=cq["message"]["message_id"],
                )
            except Exception:
                logger.debug("Failed to delete previous recent message", exc_info=True)

            try:
                _, raw_offset = data.split("::", 1)
                offset = int(raw_offset)
            except Exception:
                logger.warning("Failed to parse offset from data=%r, fallback to 0", data)
                offset = 0

        logger.debug("RecentHandler: user_id=%s offset=%s", user_id, offset)
        self._render_page(chat_id, user_id, offset)

        if hasattr(self.tg, "answerCallbackQuery"):
            self.tg.answerCallbackQuery(callback_query_id=cq["id"])

        return False

    # ---------- Internal helpers ----------

    def _footer_keyboard(self) -> Dict[str, Any]:
        """
        Common footer keyboard with "add expense" and "main menu" buttons.
        """
        return {
            "inline_keyboard": [
                [
                    {
                        "text": "➕ Добавить расход",
                        "callback_data": MENU_ADD,
                    }
                ],
                [
                    {
                        "text": "🏠 В главное меню",
                        "callback_data": MENU_MAIN,
                    }
                ],
            ]
        }

    def _render_page(self, chat_id: int, user_id: int, offset: int) -> None:
        """
        Fetch and render one "page" of recent expenses.

        Parameters
        ----------
        chat_id : int
            Telegram chat id.
        user_id : int
            Telegram user id.
        offset : int
            Number of records to skip from the newest ones.
        """
        rows = self._select_recent_slice(user_id, limit=self.n, offset=offset)

        if not rows and offset == 0:
            text = (
                "🕘 Последние записи\n\n"
                "Пока нет ни одной записи. "
                "Добавьте первую через меню «➕ Добавить расход»."
            )
            keyboard = self._footer_keyboard()
            self.tg.sendMessage(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            return

        if not rows:
            text = "Больше записей нет 🙂"
            keyboard = self._footer_keyboard()
            self.tg.sendMessage(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            return

        # Build lines: date  amount  category  store  (note)
        lines: List[str] = ["🕘 Последние записи:\n"]
        for created_at, category, store, amount, note in rows:
            # created_at: "YYYY-MM-DD HH:MM"
            ts = (created_at or "")[:16]
            try:
                amt_str = f"{float(amount):.2f}"
            except Exception:
                amt_str = str(amount)

            line = f"{ts} · {amt_str} ₽ · {category} · {store}"
            if note:
                line += f" · ({note})"
            lines.append(line)

        text = "\n".join(lines)

        keyboard = self._footer_keyboard()

        if len(rows) == self.n:
            next_offset = offset + self.n
            keyboard["inline_keyboard"].insert(
                0,
                [
                    {
                        "text": "Показать ещё",
                        "callback_data": f"RECENT_MORE::{next_offset}",
                    }
                ],
            )

        self.tg.sendMessage(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    def _select_recent_slice(
        self,
        user_id: int,
        limit: int,
        offset: int = 0,
    ) -> List[tuple]:
        """
        Fetch a slice of recent expenses for the user.

        Parameters
        ----------
        user_id : int
            Telegram user id.
        limit : int
            Max number of rows to return.
        offset : int, optional
            Number of newest rows to skip, by default 0.

        Returns
        -------
        list of tuple
            Rows (created_at, category, store, amount, note) ordered by created_at DESC.
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT created_at, category, store, amount, note
            FROM expenses
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, limit, offset),
        )
        rows = cur.fetchall()
        logger.debug(
            "Recent slice: user_id=%s offset=%s limit=%s got=%s",
            user_id,
            offset,
            limit,
            len(rows),
        )
        return rows
