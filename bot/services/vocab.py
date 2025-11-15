from typing import List, Set
from ..repo.expenses_repo import select_user_categories, select_user_stores

DEFAULT_CATEGORIES = ["Еда", "Транспорт", "Кафе", "Аптека", "Развлечения"]
DEFAULT_STORES = ["Пятёрочка", "Магнит", "Дикси", "Лента", "Ozon"]


def get_user_categories(conn, user_id: int) -> List[str]:
    """
    Compose user's category list without dedicated dictionary tables.

    Parameters
    ----------
    conn : sqlite3.Connection
        Open SQLite connection.
    user_id : int
        Telegram user identifier.

    Returns
    -------
    list of str
        Sorted union of DEFAULT_CATEGORIES and user's distinct categories from expenses.
    """
    used = select_user_categories(conn, user_id)
    merged: Set[str] = set(x.strip() for x in DEFAULT_CATEGORIES) | set(x.strip() for x in used)
    return sorted(merged, key=lambda s: s.lower())


def get_user_stores(conn, user_id: int) -> List[str]:
    """
    Compose user's store list without dedicated dictionary tables.

    Parameters
    ----------
    conn : sqlite3.Connection
        Open SQLite connection.
    user_id : int
        Telegram user identifier.

    Returns
    -------
    list of str
        Sorted union of DEFAULT_STORES and user's distinct stores from expenses.
    """
    used = select_user_stores(conn, user_id)
    merged: Set[str] = set(x.strip() for x in DEFAULT_STORES) | set(x.strip() for x in used)
    return sorted(merged, key=lambda s: s.lower())
