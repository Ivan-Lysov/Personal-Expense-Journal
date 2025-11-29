import csv
import datetime
import html
import io
import logging
from typing import Any, Dict, List

from bot.constants import MENU_ADD, MENU_EXPORT_CSV, MENU_MAIN
from bot.repo.expenses_repo import select_all_for_user

from ..handler import Handler

logger = logging.getLogger("expense_bot.export_csv")


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
        Build CSV export for the user and send it as a file (sendDocument).

        Falls back to text block with <code> if file upload fails.

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
            text = "⬇️ Экспорт CSV\n\n" "Пока нет расходов для экспорта."
            self.tg.sendMessage(chat_id=chat_id, text=text, parse_mode="HTML")
        else:
            csv_text = self._build_csv(rows)

            csv_text_with_bom = "\ufeff" + csv_text
            csv_bytes = csv_text_with_bom.encode("utf-8")

            today = datetime.date.today().isoformat()
            filename = f"expenses_{today}.csv"

            caption = "⬇️ Экспорт CSV\n\n" f"Файл <b>{filename}</b> содержит все ваши расходы " "на момент выгрузки."

            try:
                self.tg.sendDocument(
                    chat_id=chat_id,
                    filename=filename,
                    content=csv_bytes,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=self._footer_keyboard(),
                )
            except Exception as exc:
                logger.exception("sendDocument failed, fallback to text CSV: %r", exc)

                safe_csv = html.escape(csv_text, quote=False)
                text = (
                    "⬇️ Экспорт CSV (текстовый вариант)\n\n"
                    "Скопируйте содержимое блока и сохраните в файл, "
                    f"например <b>{filename}</b>:\n\n"
                    f"<code>{safe_csv}</code>"
                )
                self.tg.sendMessage(
                    chat_id=chat_id,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=self._footer_keyboard(),
                )

        if hasattr(self.tg, "answerCallbackQuery"):
            self.tg.answerCallbackQuery(callback_query_id=cq["id"])

        return False

    def _footer_keyboard(self) -> dict:
        """
        Inline keyboard used under report/export messages.
        """
        return {
            "inline_keyboard": [
                [
                    {"text": "➕ Добавить расход", "callback_data": MENU_ADD},
                ],
                [
                    {"text": "🏠 В главное меню", "callback_data": MENU_MAIN},
                ],
            ]
        }

    def _build_csv(self, rows: list[tuple]) -> str:
        """
        Build CSV text for all user's expenses.

        Format:
        - Delimiter: ';'  (better for Excel in ru-RU locale)
        - Encoding: UTF-8 (BOM will be added before sending)
        - Header: created_at;category;store;amount;note
        """
        buf = io.StringIO()
        writer = csv.writer(
            buf,
            delimiter=";",
            lineterminator="\n",
            quoting=csv.QUOTE_MINIMAL,
        )

        writer.writerow(["created_at", "category", "store", "amount", "note"])

        for created_at, category, store, amount, note in rows:
            amount_str = f"{float(amount):.2f}"
            writer.writerow(
                [
                    created_at,
                    category or "",
                    store or "",
                    amount_str,
                    note or "",
                ]
            )

        return buf.getvalue()

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
            if any(ch in v for ch in [",", '"', "\n"]):
                v = v.replace('"', '""')
                v = f'"{v}"'
            out.append(v)
        return ",".join(out)
