from typing import Any, Dict
from ..handler import Handler
from bot.constants import MENU_HELP, MENU_MAIN


class HelpMenuHandler(Handler):
    """
    Handle main-menu help requests.

    This handler reacts to the MENU_HELP callback and sends
    a nicely formatted HTML help message with all features.
    """

    def __init__(self, telegram_client):
        """
        Parameters
        ----------
        telegram_client : Any
            Module or object providing sendMessage() and answerCallbackQuery().
        """
        self.tg = telegram_client

    def can_handle(self, update: Dict[str, Any]) -> bool:
        cq = update.get("callback_query")
        if not cq:
            return False
        return cq.get("data") == MENU_HELP

    def handle(self, update: Dict[str, Any]) -> bool:
        cq = update["callback_query"]
        chat_id = cq["message"]["chat"]["id"]

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

        text = (
            "<b>ℹ️ Справка по боту учёта расходов</b>\n\n"
            "Этот бот позволяет быстро фиксировать ежедневные траты.\n"
            "Доступные функции:\n\n"
            "• <b>➕ Добавить</b> — по шагам указать категорию, магазин, сумму \
                  и заметку.\n"
            "• <b>🧾 Последние</b> — список последних 10 записей.\n"
            "• <b>➗ Сумма последних 10 10</b> — сумма последних 10 расходов.\n"
            "• <b>📅 Отчёт (месяц)</b> — сумма по категориям \
                за текущий месяц.\n"
            "• <b>⬇️ CSV</b> — экспорт всех расходов в формате CSV.\n\n"
            "<b>Как добавить расход:</b>\n"
            "1) Нажмите «➕ Добавить».\n"
            "2) Выберите категорию или создайте новую.\n"
            "3) Выберите магазин или добавьте новый.\n"
            "4) Введите сумму (например: 125.50).\n"
            "5) Добавьте заметку или пропустите.\n"
            "6) Проверьте данные и нажмите «Сохранить».\n\n"
            "<b>Как открыть CSV в Excel:</b>\n"
            "1) Скопируйте CSV из сообщения.\n"
            "2) Сохраните в файл с кодировкой UTF-8.\n"
            "3) В Excel: Данные → Из текста/CSV → выбрать \
                разделитель «Запятая».\n\n"
            "Если возникнут вопросы — просто напишите /help."
        )

        self.tg.sendMessage(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )

        if hasattr(self.tg, "answerCallbackQuery"):
            self.tg.answerCallbackQuery(callback_query_id=cq["id"])

        return False
