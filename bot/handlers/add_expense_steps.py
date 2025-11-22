from typing import Any, Dict, Tuple, Callable

from bot.handler import Handler
from bot.constants import (
    STATE_ASK_CATEGORY,
    STATE_ASK_STORE,
    STATE_ASK_AMOUNT,
    STATE_ASK_NOTE,
    STATE_CONFIRM,
    MENU_ADD,
    MENU_MAIN,
)
from bot.repo.state_repo import get_state, set_state, reset_state
from bot.repo.expenses_repo import insert_expense
from bot.services.parsing import parse_amount


def parse_callback(data: str) -> Tuple[str, str]:
    """
    Parse callback_data into (kind, value).

    Parameters
    ----------
    data : str
        Raw callback data like 'CATEGORY::Food' or 'CONFIRM::SAVE'.

    Returns
    -------
    tuple[str, str]
        (kind, value). For 'CANCEL' → ('CANCEL',''). Unknown → ('','').
    """
    if data == "CANCEL":
        return "CANCEL", ""
    if "::" in data:
        kind, value = data.split("::", 1)
        return kind, value
    return "", ""


class AddExpenseStepsHandler(Handler):
    """
    Multi-step "Add expense" dialog (FSM) with flat routing and clean UX.

    What this handler does
    ----------------------
    • Drives states: ASK_CATEGORY → ASK_STORE → ASK_AMOUNT → ASK_NOTE → CONFIRM.
    • Accepts both callback buttons and typed text (for NEW category/store, amount, note).
    • Each step deletes the previous prompt message and sends a new one (HTML).
    • Always shows a '❌ Отмена' button on steps with keyboard.

    Callback namespaces
    -------------------
    CATEGORY::X | CATEGORY::NEW
    STORE::X    | STORE::NEW
    NOTE::SKIP
    CONFIRM::SAVE | CONFIRM::CANCEL
    CANCEL

    Text input (payload['expect_text'])
    -----------------------------------
    'CATEGORY' → new category name
    'STORE'    → new store name
    'AMOUNT'   → positive number (',' or '.')
    'NOTE'     → free text note (optional)
    """

    def __init__(self, telegram_client, conn, categories_provider, stores_provider):
        """
        Parameters
        ----------
        telegram_client : Any
            Module with Telegram Bot API functions (sendMessage, deleteMessage, answerCallbackQuery, ...).
        conn : sqlite3.Connection
            Open SQLite connection.
        categories_provider : Callable[[sqlite3.Connection, int], list[str]]
            Defaults distinct-used categories for a user (not used for rendering here).
        stores_provider : Callable[[sqlite3.Connection, int], list[str]]
            Defaults distinct-used stores for a user.
        """
        self.tg = telegram_client
        self.conn = conn
        self.get_user_categories = categories_provider
        self.get_user_stores = stores_provider

        self.text_handlers: Dict[str, Callable[[int, int, str, Dict[str, Any]], bool]] = {
            "CATEGORY": self._text_new_category,
            "STORE": self._text_new_store,
            "AMOUNT": self._text_amount,
            "NOTE": self._text_note,
        }

        self.callback_handlers: Dict[str, Callable[[int, int, str, Dict[str, Any]], bool]] = {
            "CATEGORY": self._cb_category,
            "STORE": self._cb_store,
            "NOTE": self._cb_note,
            "CONFIRM": self._cb_confirm,
            "CANCEL": self._cb_cancel,
        }

    def can_handle(self, update: Dict[str, Any]) -> bool:
        if "callback_query" in update:
            data = update["callback_query"].get("data", "")
            kind, _ = parse_callback(data)
            return kind in self.callback_handlers

        msg = update.get("message")
        if not msg:
            return False
        if isinstance(msg.get("text"), str):
            user_id = msg["from"]["id"]
            state, payload = get_state(self.conn, user_id)
            expect = payload.get("expect_text")
            return expect in self.text_handlers and state in (
                STATE_ASK_CATEGORY, STATE_ASK_STORE, STATE_ASK_AMOUNT, STATE_ASK_NOTE
            )
        return False

    def handle(self, update: Dict[str, Any]) -> bool:
        if "callback_query" in update:
            cq = update["callback_query"]
            chat_id = cq["message"]["chat"]["id"]
            user_id = cq["from"]["id"]
            data = cq.get("data", "")
            kind, value = parse_callback(data)

            handler = self.callback_handlers.get(kind)
            if not handler:
                return True

            consumed = handler(chat_id, user_id, value, update)
            if consumed is False and hasattr(self.tg, "answerCallbackQuery"):
                self.tg.answerCallbackQuery(callback_query_id=cq["id"])
            return consumed

        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        text = (msg.get("text") or "").strip()

        state, payload = get_state(self.conn, user_id)
        expect = payload.get("expect_text")

        handler = self.text_handlers.get(expect or "")
        if not handler:
            return True
        return handler(chat_id, user_id, text, payload)

    def _cb_cancel(self, chat_id: int, user_id: int, _: str, __: Dict[str, Any]) -> bool:
        # Delete last prompt first (payload still has last_msg_id), then reset.
        self._delete_last(chat_id, user_id)
        reset_state(self.conn, user_id)
        self._say_html(chat_id, "Операция отменена. Откройте меню командой <b>/start</b>.")
        return False  # consumed

    def _cb_category(self, chat_id: int, user_id: int, value: str, _: Dict[str, Any]) -> bool:
        state, payload = get_state(self.conn, user_id)
        if state != STATE_ASK_CATEGORY:
            return True

        if value == "NEW":
            payload["expect_text"] = "CATEGORY"
            set_state(self.conn, user_id, STATE_ASK_CATEGORY, payload)
            self._send_and_remember(chat_id, user_id, "Введите <b>новую категорию</b> текстом. Или нажмите «❌ Отмена».")
            return False

        payload["category"] = value
        payload["expect_text"] = None
        set_state(self.conn, user_id, STATE_ASK_STORE, payload)
        self._render_store_choice(chat_id, user_id)
        return False

    def _cb_store(self, chat_id: int, user_id: int, value: str, _: Dict[str, Any]) -> bool:
        state, payload = get_state(self.conn, user_id)
        if state != STATE_ASK_STORE:
            return True

        if value == "NEW":
            payload["expect_text"] = "STORE"
            set_state(self.conn, user_id, STATE_ASK_STORE, payload)
            self._send_and_remember(chat_id, user_id, "Введите <b>новый магазин</b> текстом. Или нажмите «❌ Отмена».")
            return False

        payload["store"] = value
        payload["expect_text"] = "AMOUNT"
        set_state(self.conn, user_id, STATE_ASK_AMOUNT, payload)
        self._prompt_amount(chat_id, user_id)
        return False

    def _cb_note(self, chat_id: int, user_id: int, value: str, _: Dict[str, Any]) -> bool:
        state, payload = get_state(self.conn, user_id)
        if state != STATE_ASK_NOTE:
            return True

        if value == "SKIP":
            payload["note"] = ""
            payload["expect_text"] = None
            set_state(self.conn, user_id, STATE_CONFIRM, payload)
            self._render_confirm(chat_id, user_id, payload)
            return False

        return True

    def _cb_confirm(self, chat_id: int, user_id: int, value: str, _: Dict[str, Any]) -> bool:
        state, payload = get_state(self.conn, user_id)
        if state != STATE_CONFIRM:
            return True

        if value == "SAVE":
            category = payload.get("category")
            store = payload.get("store")
            amount = payload.get("amount")
            note = payload.get("note", "")

            if not category or not store or amount is None:
                # Clean UX: delete last prompt; reset; say error.
                self._delete_last(chat_id, user_id)
                reset_state(self.conn, user_id)
                self._say_html(
                    chat_id,
                    "Не удалось сохранить — отсутствуют данные. "
                    "Попробуйте снова: <b>/start</b>."
                )
                return False

            insert_expense(
                self.conn,
                user_id,
                str(category),
                str(store),
                float(amount),
                str(note or ""),
            )
            # Clean up last prompt and reset FSM
            self._delete_last(chat_id, user_id)
            reset_state(self.conn, user_id)

            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "➕ Добавить ещё расход",
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

            self.tg.sendMessage(
                chat_id=chat_id,
                text="Готово ✔️ <b>Запись сохранена.</b>",
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            return False

        if value == "CANCEL":
            self._delete_last(chat_id, user_id)
            reset_state(self.conn, user_id)
            self._say_html(chat_id, "Отменено. Возврат в меню: <b>/start</b>")
            return False
    
    # ---------- Text handlers (by expect_text) ----------

    def _text_new_category(self, chat_id: int, user_id: int, text: str, payload: Dict[str, Any]) -> bool:
        if not text:
            self._send_and_remember(chat_id, user_id, "Категория не должна быть пустой. Введите название или нажмите «❌ Отмена».")
            return False
        payload["category"] = text
        payload["expect_text"] = None
        set_state(self.conn, user_id, STATE_ASK_STORE, payload)
        self._render_store_choice(chat_id, user_id)
        return False

    def _text_new_store(self, chat_id: int, user_id: int, text: str, payload: Dict[str, Any]) -> bool:
        if not text:
            self._send_and_remember(chat_id, user_id, "Магазин не должен быть пустым. Введите название или нажмите «❌ Отмена».")
            return False
        payload["store"] = text
        payload["expect_text"] = "AMOUNT"
        set_state(self.conn, user_id, STATE_ASK_AMOUNT, payload)
        self._prompt_amount(chat_id, user_id)
        return False

    def _text_amount(self, chat_id: int, user_id: int, text: str, payload: Dict[str, Any]) -> bool:
        amount = parse_amount(text)
        if amount is None:
            self._send_and_remember(chat_id, user_id, "Сумма должна быть <b>положительным числом</b>. Пример: <b>125.50</b>")
            return False
        payload["amount"] = amount
        payload["expect_text"] = "NOTE"
        set_state(self.conn, user_id, STATE_ASK_NOTE, payload)
        self._prompt_note(chat_id, user_id)
        return False

    def _text_note(self, chat_id: int, user_id: int, text: str, payload: Dict[str, Any]) -> bool:
        payload["note"] = text
        payload["expect_text"] = None
        set_state(self.conn, user_id, STATE_CONFIRM, payload)
        self._render_confirm(chat_id, user_id, payload)
        return False

    # ---------- Rendering / Telegram helpers ----------

    def _render_store_choice(self, chat_id: int, user_id: int) -> None:
        stores = self.get_user_stores(self.conn, user_id)
        keyboard = {
            "inline_keyboard": [
                *[[{"text": name, "callback_data": f"STORE::{name}"}] for name in stores],
                [{"text": "➕ Новый магазин", "callback_data": "STORE::NEW"}],
                [{"text": "❌ Отмена", "callback_data": "CANCEL"}],
            ]
        }
        self._send_and_remember(chat_id, user_id, "<b>Выберите магазин</b>:", keyboard)

    def _prompt_amount(self, chat_id: int, user_id: int) -> None:
        keyboard = {
            "inline_keyboard": [
                [{"text": "❌ Отмена", "callback_data": "CANCEL"}],
            ]
        }
        self._send_and_remember(
            chat_id,
            user_id,
            "Введите сумму (пример: <b>125.50</b>). Или нажмите «❌ Отмена».",
            keyboard,
        )

    def _prompt_note(self, chat_id: int, user_id: int) -> None:
        keyboard = {
            "inline_keyboard": [
                [{"text": "Пропустить заметку", "callback_data": "NOTE::SKIP"}],
                [{"text": "❌ Отмена", "callback_data": "CANCEL"}],
            ]
        }
        self._send_and_remember(chat_id, user_id, "<b>Введите заметку</b> (или нажмите «Пропустить заметку»):", keyboard)

    def _render_confirm(self, chat_id: int, user_id: int, payload: Dict[str, Any]) -> None:
        category = payload.get("category", "—")
        store = payload.get("store", "—")
        amount = payload.get("amount", "—")
        note = payload.get("note", "")
        text = (
            "<b>Проверьте данные</b>:\n"
            f"<b>Категория:</b> {category}\n"
            f"<b>Магазин:</b> {store}\n"
            f"<b>Сумма:</b> {amount}\n"
            f"<b>Заметка:</b> {note if note else '—'}"
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": "💾 Сохранить", "callback_data": "CONFIRM::SAVE"}],
                [{"text": "❌ Отмена", "callback_data": "CONFIRM::CANCEL"}],
            ]
        }
        self._send_and_remember(chat_id, user_id, text, keyboard)

    def _send_and_remember(self, chat_id: int,
                           user_id: int, text: str, reply_markup: Dict[str, Any] | None = None) -> None:
        """
        Send a message (HTML), delete previous prompt (if any), remember new message_id in payload.

        Parameters
        ----------
        chat_id : int
            Target chat id.
        user_id : int
            Telegram user id.
        text : str
            HTML text to send.
        reply_markup : dict or None
            Inline keyboard.
        """
        # Delete previous prompt if we know its message_id
        state, payload = get_state(self.conn, user_id)
        last_id = payload.get("last_msg_id")
        if isinstance(last_id, int):
            try:
                self.tg.deleteMessage(chat_id=chat_id, message_id=last_id)
            except Exception:
                pass

        if reply_markup:
            msg = self.tg.sendMessage(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="HTML")
        else:
            msg = self.tg.sendMessage(chat_id=chat_id, text=text, parse_mode="HTML")

        try:
            new_id = int(msg.get("message_id"))
            payload["last_msg_id"] = new_id
            set_state(self.conn, user_id, state, payload)
        except Exception:
            pass

    def _delete_last(self, chat_id: int, user_id: int) -> None:
        """
        Try to delete last prompt message (if payload remembers it).
        """
        state, payload = get_state(self.conn, user_id)
        last_id = payload.get("last_msg_id")
        if isinstance(last_id, int):
            try:
                self.tg.deleteMessage(chat_id=chat_id, message_id=last_id)
            except Exception:
                pass

    def _say_html(self, chat_id: int, text: str) -> None:
        """
        Send a one-off HTML message (no remembering, no deletion).
        """
        self.tg.sendMessage(chat_id=chat_id, text=text, parse_mode="HTML")
