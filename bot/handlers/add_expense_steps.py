from typing import Any, Dict, Tuple, Callable

from bot.handler import Handler
from bot.constants import (
    STATE_ASK_CATEGORY,
    STATE_ASK_STORE,
    STATE_ASK_AMOUNT,
    STATE_ASK_NOTE,
    STATE_CONFIRM,
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
        A (kind, value) pair. For 'CANCEL' returns ('CANCEL', '').
    """
    if data == "CANCEL":
        return "CANCEL", ""
    if "::" in data:
        kind, value = data.split("::", 1)
        return kind, value
    # unknown namespace
    return "", ""


class AddExpenseStepsHandler(Handler):
    """
    Drive the multi-step "Add expense" dialog (FSM) with flat routing.

    Supported callbacks
    -------------------
    - CATEGORY::X | CATEGORY::NEW
    - STORE::X    | STORE::NEW
    - NOTE::SKIP
    - CONFIRM::SAVE | CONFIRM::CANCEL
    - CANCEL

    Supported text input (by expected key in payload.expect_text)
    -------------------------------------------------------------
    - 'CATEGORY' : new category name
    - 'STORE'    : new store name
    - 'AMOUNT'   : amount like '125.50' or '125,50'
    - 'NOTE'     : free text note
    """

    def __init__(self, telegram_client, conn, categories_provider, stores_provider):
        self.tg = telegram_client
        self.conn = conn
        self.get_user_categories = categories_provider
        self.get_user_stores = stores_provider

        # Text handlers mapping by `expect_text`
        self.text_handlers: Dict[str, Callable[[int, int, str, Dict[str, Any]], bool]] = {
            "CATEGORY": self._text_new_category,
            "STORE": self._text_new_store,
            "AMOUNT": self._text_amount,
            "NOTE": self._text_note,
        }

        # Callback handlers mapping by kind
        self.callback_handlers: Dict[str, Callable[[int, int, str, Dict[str, Any]], bool]] = {
            "CATEGORY": self._cb_category,
            "STORE": self._cb_store,
            "NOTE": self._cb_note,
            "CONFIRM": self._cb_confirm,
            "CANCEL": self._cb_cancel,
        }

    # ---------- Dispatcher contract ----------

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
                return True  # let others handle unknown callbacks

            consumed = handler(chat_id, user_id, value, update)
            # Ack only if we actually handled it (consumed)
            if consumed and hasattr(self.tg, "answerCallbackQuery"):
                self.tg.answerCallbackQuery(callback_query_id=cq["id"])
            return consumed

        # message.text path
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        text = (msg.get("text") or "").strip()

        state, payload = get_state(self.conn, user_id)
        expect = payload.get("expect_text")

        handler = self.text_handlers.get(expect or "")
        if not handler:
            return True  # not our text
        return handler(chat_id, user_id, text, payload)

    # ---------- Callback handlers (flat, early-return) ----------

    def _cb_cancel(self, chat_id: int, user_id: int, _: str, __: Dict[str, Any]) -> bool:
        reset_state(self.conn, user_id)
        self._say(chat_id, "Операция отменена. Откройте меню командой /start.")
        return False  # consumed

    def _cb_category(self, chat_id: int, user_id: int, value: str, _: Dict[str, Any]) -> bool:
        state, payload = get_state(self.conn, user_id)
        if state != STATE_ASK_CATEGORY:
            return True  # not our step

        if value == "NEW":
            payload["expect_text"] = "CATEGORY"
            set_state(self.conn, user_id, STATE_ASK_CATEGORY, payload)
            self._say(chat_id, "Введите новую категорию текстом. Или нажмите «❌ Отмена».")
            return False

        # Choose existing category
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
            self._say(chat_id, "Введите новый магазин текстом. Или нажмите «❌ Отмена».")
            return False

        payload["store"] = value
        payload["expect_text"] = "AMOUNT"
        set_state(self.conn, user_id, STATE_ASK_AMOUNT, payload)
        self._prompt_amount(chat_id)
        return False

    def _cb_note(self, chat_id: int, user_id: int, value: str, _: Dict[str, Any]) -> bool:
        state, payload = get_state(self.conn, user_id)
        if state != STATE_ASK_NOTE:
            return True

        if value == "SKIP":
            payload["note"] = ""
            payload["expect_text"] = None
            set_state(self.conn, user_id, STATE_CONFIRM, payload)
            self._render_confirm(chat_id, payload)
            return False

        # Unknown NOTE::* variant → let others try
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
                reset_state(self.conn, user_id)
                self._say(chat_id, "Не удалось сохранить — отсутствуют данные. Попробуйте снова: /start.")
                return False

            insert_expense(self.conn, user_id, str(category), str(store), float(amount), str(note or ""))
            reset_state(self.conn, user_id)
            self._say(chat_id, "Готово ✔️ Запись сохранена.")
            return False

        if value == "CANCEL":
            reset_state(self.conn, user_id)
            self._say(chat_id, "Отменено. Возврат в меню: /start")
            return False

        return True

    # ---------- Text handlers (by expect_text) ----------

    def _text_new_category(self, chat_id: int, user_id: int, text: str, payload: Dict[str, Any]) -> bool:
        if not text:
            self._say(chat_id, "Категория не должна быть пустой. Введите название или нажмите «❌ Отмена».")
            return False
        payload["category"] = text
        payload["expect_text"] = None
        set_state(self.conn, user_id, STATE_ASK_STORE, payload)
        self._render_store_choice(chat_id, user_id)
        return False

    def _text_new_store(self, chat_id: int, user_id: int, text: str, payload: Dict[str, Any]) -> bool:
        if not text:
            self._say(chat_id, "Магазин не должен быть пустым. Введите название или нажмите «❌ Отмена».")
            return False
        payload["store"] = text
        payload["expect_text"] = "AMOUNT"
        set_state(self.conn, user_id, STATE_ASK_AMOUNT, payload)
        self._prompt_amount(chat_id)
        return False

    def _text_amount(self, chat_id: int, user_id: int, text: str, payload: Dict[str, Any]) -> bool:
        amount = parse_amount(text)
        if amount is None:
            self._say(chat_id, "Сумма должна быть положительным числом. Пример: 125.50")
            return False
        payload["amount"] = amount
        payload["expect_text"] = "NOTE"
        set_state(self.conn, user_id, STATE_ASK_NOTE, payload)
        self._prompt_note(chat_id)
        return False

    def _text_note(self, chat_id: int, user_id: int, text: str, payload: Dict[str, Any]) -> bool:
        payload["note"] = text
        payload["expect_text"] = None
        set_state(self.conn, user_id, STATE_CONFIRM, payload)
        self._render_confirm(chat_id, payload)
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
        self._say(chat_id, "Выберите магазин:", keyboard)

    def _prompt_amount(self, chat_id: int) -> None:
        self._say(chat_id, "Введите сумму (пример: 125.50). Или нажмите «❌ Отмена».")

    def _prompt_note(self, chat_id: int) -> None:
        keyboard = {
            "inline_keyboard": [
                [{"text": "Пропустить заметку", "callback_data": "NOTE::SKIP"}],
                [{"text": "❌ Отмена", "callback_data": "CANCEL"}],
            ]
        }
        self._say(chat_id, "Введите заметку (или нажмите «Пропустить заметку»):", keyboard)

    def _render_confirm(self, chat_id: int, payload: Dict[str, Any]) -> None:
        category = payload.get("category", "—")
        store = payload.get("store", "—")
        amount = payload.get("amount", "—")
        note = payload.get("note", "")
        text = (
            "Проверьте данные:\n"
            f"• Категория: {category}\n"
            f"• Магазин: {store}\n"
            f"• Сумма: {amount}\n"
            f"• Заметка: {note if note else '—'}"
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": "💾 Сохранить", "callback_data": "CONFIRM::SAVE"}],
                [{"text": "❌ Отмена", "callback_data": "CONFIRM::CANCEL"}],
            ]
        }
        self._say(chat_id, text, keyboard)

    def _say(self, chat_id: int, text: str, reply_markup: Dict[str, Any] | None = None) -> None:
        if reply_markup:
            self.tg.sendMessage(chat_id=chat_id, text=text, reply_markup=reply_markup)
        else:
            self.tg.sendMessage(chat_id=chat_id, text=text)
