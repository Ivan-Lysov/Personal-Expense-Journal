from bot.repo.state_repo import get_state, set_state
from typing import Optional, Dict, Any


def parse_amount(text: str) -> Optional[float]:
    """
    Parse user-entered amount from a free-form string.

    This parser is intentionally simple for MVP:
    - strips whitespace,
    - replaces comma with dot,
    - rejects negative or zero,
    - returns None on failure.

    Parameters
    ----------
    text : str
        Raw user-entered text (e.g. "125,50", "  200.0 ").

    Returns
    -------
    float or None
        Parsed positive float if valid, otherwise None.
    """
    if not isinstance(text, str):
        return None
    s = text.strip().replace(",", ".")
    # Allow leading "+"; reject minus
    if s.startswith("+"):
        s = s[1:].lstrip()

    try:
        value = float(s)
    except Exception:
        return None

    if value <= 0:
        return None
    return value


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
        f"• <b>Категория:</b> {category}\n"
        f"• <b>Магазин:</b> {store}\n"
        f"• <b>Сумма:</b> {amount}\n"
        f"• <b>Заметка:</b> {note if note else '—'}"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "💾 Сохранить", "callback_data": "CONFIRM::SAVE"}],
            [{"text": "❌ Отмена", "callback_data": "CONFIRM::CANCEL"}],
        ]
    }
    self._send_and_remember(chat_id, user_id, text, keyboard)


def _send_and_remember(self, chat_id: int, user_id: int, text: str, reply_markup: Dict[str, Any] | None = None) -> None:
    """
    Send a message in HTML mode, delete previous prompt (if any), and remember the new message_id in payload.

    Parameters
    ----------
    chat_id : int
        Target chat id.
    user_id : int
        Telegram user id.
    text : str
        Message HTML.
    reply_markup : dict or None
        Inline keyboard to attach.
    """
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
