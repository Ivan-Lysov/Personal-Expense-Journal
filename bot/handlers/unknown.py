from ..handler import Handler

class UnknownCallbackHandler(Handler):
    """
    Catch-all for callback_query that were not handled by previous handlers.
    """

    def __init__(self, telegram_client):
        self.tg = telegram_client

    def can_handle(self, update: dict) -> bool:
        return "callback_query" in update

    def handle(self, update: dict) -> bool:
        cq = update["callback_query"]
        chat_id = cq["message"]["chat"]["id"]
        self.tg.sendMessage(chat_id=chat_id, text="Не понял эту кнопку. Откройте меню командой /start.")
        if hasattr(self.tg, "answerCallbackQuery"):
            self.tg.answerCallbackQuery(callback_query_id=cq["id"])
        return False


class UnknownTextHandler(Handler):
    """
    Catch-all for plain text messages that do not match any command/FSM step.
    """

    def __init__(self, telegram_client):
        self.tg = telegram_client

    def can_handle(self, update: dict) -> bool:
        msg = update.get("message")
        if not msg:
            return False
        return isinstance(msg.get("text"), str)

    def handle(self, update: dict) -> bool:
        chat_id = update["message"]["chat"]["id"]
        self.tg.sendMessage(chat_id=chat_id, text="Не понял сообщение. Нажмите /start, чтобы открыть меню.")
        return False
