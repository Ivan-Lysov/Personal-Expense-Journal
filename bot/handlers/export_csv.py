from typing import Any, Dict, List
import html

from ..handler import Handler
from bot.constants import MENU_EXPORT_CSV
from bot.repo.expenses_repo import select_all_for_user


class CsvExportHandler(Handler):
    """
    Handle CSV export requests from the main menu.

    This handler reacts to the `MENU_EXPORT_CSV` callback:
    - Fetches all expenses for the user.
    - Builds a plain CSV string (UTF-8, comma-separated, quoted where needed).
    - Sends the CSV enclosed into HTML <code> block so user can copy-paste it
      into a local file (e.g. data.csv).

    Notes
    -----
    This is a lightweight MVP: the CSV is sent as text, not as a file.
    For large histories the message may hit Telegram's length limit.
    """

    def __init__(self, telegram_client, conn):
        """
        Parameters
        ----------
        telegram_client : Any
            Module or object with `sendMessage` and `answerCallbackQuery`.
        conn : sqlite3.Connection
            Open SQLite connection.
        """
        self.tg = telegram_client
        self.conn = conn

    def can_handle(self, update: Dict[str, Any]) -> bool:
        """
        Check if this handler should process the given update.

        It only handles callback queries with data == MENU_EXPORT_CSV.
        """
        cq = update.get("callback_query")
        if not cq:
            return False
        return cq.get("data") == MENU_EXPORT_CSV

    def handle(self, update: Dict[str, Any]) -> bool:
        """
        Build CSV export for the user and send it as a text message.

        Returns
        -------
        bool
            False, as this handler fully consumes the update.
        """
        cq = update["callback_query"]
        chat_id = cq["message"]["chat"]["id"]
        user_id = cq["from"]["id"]

        rows = select_all_for_user(self.conn, user_id)

        if not rows:
            text = (
                "⬇️ Экспорт CSV\n\n"
                "Пока нет расходов для экспорта."
            )
            self.tg.sendMessage(chat_id=chat_id, text=text, parse_mode="HTML")
        else:
            csv_text = self._build_csv(rows)
            # Escape for HTML and wrap into <code> block
            safe_csv = html.escape(csv_text, quote=False)
            text = (
                "⬇️ Экспорт CSV\n\n"
                "Скопируйте содержимое блока и сохраните в файл, например <b>data.csv</b>:\n\n"
                f"<code>{safe_csv}</code>"
            )
            self.tg.sendMessage(chat_id=chat_id, text=text, parse_mode="HTML")

        if hasattr(self.tg, "answerCallbackQuery"):
            self.tg.answerCallbackQuery(callback_query_id=cq["id"])

        return False

    def _build_csv(self, rows: List[Any]) -> str:
        """
        Build CSV string (header + rows) from expense rows.

        Parameters
        ----------
        rows : list
            Rows from `select_all_for_user`, each with
            created_at, category, store, amount, note.

        Returns
        -------
        str
            CSV data as a single string with '\n' separators.
        """
        header = ["created_at", "category", "store", "amount", "note"]
        lines: List[str] = []
        lines.append(self._join_csv_row(header))

        for r in rows:
            created_at = str(r["created_at"])
            category = str(r["category"] if r["category"] is not None else "")
            store = str(r["store"] if r["store"] is not None else "")
            amount = f"{float(r['amount']):.2f}"
            note = str(r["note"] if r["note"] is not None else "")
            lines.append(self._join_csv_row([created_at, category, store, amount, note]))

        return "\n".join(lines)

    def _join_csv_row(self, fields: List[str]) -> str:
        """
        Join a list of fields into a single CSV row.

        Parameters
        ----------
        fields : list of str
            Fields in logical order.

        Returns
        -------
        str
            Comma-separated row with double-quoted fields when needed.
        """
        out: List[str] = []
        for value in fields:
            v = value
            # Normalize newlines
            v = v.replace("\r\n", "\n").replace("\r", "\n")
            # If value contains comma, quote or newline, wrap it in quotes and escape inner quotes
            if any(ch in v for ch in [",", "\"", "\n"]):
                v = v.replace("\"", "\"\"")
                v = f"\"{v}\""
            out.append(v)
        return ",".join(out)
