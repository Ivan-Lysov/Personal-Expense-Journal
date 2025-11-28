from typing import Any, Dict
from ..handler import Handler
from bot.constants import MENU_HELP, MENU_MAIN

HELP_TEXT = (
            "<b>📘 Справка по боту учёта расходов</b>\n\n"

            "Бот помогает быстро фиксировать расходы и получать отчёты.\n"
            "Все функции доступны через главное меню (<b>/start</b>).\n\n"

            "<b>🔹 Добавить расход</b>\n"
            "Пошаговый диалог:\n"
            "1) выберите категорию\n"
            "2) укажите магазин\n"
            "3) введите сумму\n"
            "4) добавьте заметку (по желанию)\n"
            "После сохранения можно сразу добавить новый расход.\n\n"

            "<b>🔹 Последние операции</b>\n"
            "Показывает последние записи (обычно 5–10 штук).\n"
            "Используйте кнопку «Показать ещё» для следующей страницы.\n\n"

            "<b>🔹 Сумма последних 10</b>\n"
            "Выводит сумму десяти последних расходов.\n"
            "Если записей меньше — суммируются все.\n\n"

            "<b>🔹 Отчёт за месяц</b>\n"
            "Показывает статистику расходов за текущий месяц.\n"
            "Доступно: общая сумма, количество операций, средний расход.\n\n"

            "<b>🔹 Экспорт CSV</b>\n"
            "Отправляет файл <code>expenses_YYYY-MM-DD.csv</code>.\n"
            "Формат файла:\n"
            "<code>created_at;category;store;amount;note</code>\n"
            "Файл открывается в Excel/Numbers/Google Sheets.\n\n"

            "<b>🔹 Справка</b>\n"
            "Показывает этот раздел.\n\n"

            "Если что-то работает не так — просто напишите /start.\n"
        )


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

        self.tg.sendMessage(
            chat_id=chat_id,
            text=HELP_TEXT,
            parse_mode="HTML",
            reply_markup=keyboard,
        )

        if hasattr(self.tg, "answerCallbackQuery"):
            self.tg.answerCallbackQuery(callback_query_id=cq["id"])

        return False
