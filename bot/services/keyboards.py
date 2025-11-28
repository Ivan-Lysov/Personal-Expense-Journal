from bot.constants import MENU_ADD, MENU_RECENT, MENU_SUM10, MENU_REPORT, MENU_EXPORT_CSV, MENU_HELP


def main_menu_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "➕ Добавить", "callback_data": MENU_ADD},
                {"text": "🕘 Последние", "callback_data": MENU_RECENT},
            ],
            [
                {"text": "🔟 Сумма 10", "callback_data": MENU_SUM10},
                {"text": "📅 Отчёт (месяц)", "callback_data": MENU_REPORT},
            ],
            [
                {"text": "📄 CSV", "callback_data": MENU_EXPORT_CSV},
                {"text": "ℹ️ Справка", "callback_data": MENU_HELP},
            ],
        ]
    }
