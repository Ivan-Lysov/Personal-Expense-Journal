from ..handler import Handler
from bot.constants import MENU_ADD, MENU_RECENT, MENU_SUM10, MENU_REPORT, MENU_EXPORT_CSV, MENU_HELP


class StartHelpHandler(Handler):
    """
    Handle /start and /help commands. Renders the main inline menu.

    Notes
    -----
    This handler is "greedy": it consumes the update and prevents further
    handlers from running (returns False), because it already replied.
    """

    def __init__(self, telegram_client):
        self.tg = telegram_client

    def can_handle(self, update: dict) -> bool:
        msg = update.get("message")
        if not msg:
            return False
        text = msg.get("text") or ""
        return text.startswith("/start") or text.startswith("/help")

    def handle(self, update: dict) -> bool:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")

        if text.startswith("/help"):
            help_text = (
                "Бот учёта расходов.\n"
                "Используйте меню ниже, чтобы добавить расход, посмотреть последние записи, экспортировать CSV и т.д."
            )
            self.tg.sendMessage(chat_id=chat_id, text=help_text)

        keyboard = {
            "inline_keyboard": [
                [{"text": "➕ Добавить", "callback_data": MENU_ADD},
                 {"text": "🧾 Последние", "callback_data": MENU_RECENT}],
                [{"text": "➗ Сумма 10", "callback_data": MENU_SUM10},
                 {"text": "📅 Отчёт (месяц)", "callback_data": MENU_REPORT}],
                [{"text": "⬇️ CSV", "callback_data": MENU_EXPORT_CSV},
                 {"text": "ℹ️ Справка", "callback_data": MENU_HELP}],
            ]
        }
        self.tg.sendMessage(chat_id=chat_id, text="Главное меню:", reply_markup=keyboard)
        return False
