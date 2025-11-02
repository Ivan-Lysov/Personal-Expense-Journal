import sqlite3
from typing import List

def insert_expense(conn: sqlite3.Connection,
                   user_id: int,
                   category: str,
                   store: str,
                   amount: float,
                   note: str = "") -> int:
    """
    Insert a single expense row.

    Parameters
    ----------
    conn : sqlite3.Connection
        Open SQLite connection.
    user_id : int
        Telegram user identifier.
    category : str
        Category name. Stored as-is (trimmed).
    store : str
        Store/vendor name. Stored as-is (trimmed).
    amount : float
        Positive amount. Will be cast to float.
    note : str, optional
        Optional free text note, by default "".

    Returns
    -------
    int
        New expense row id.

    """
    cur = conn.execute(
        "INSERT INTO expenses(user_id, category, store, amount, note) VALUES (?,?,?,?,?)",
        (user_id, category.strip(), store.strip(), float(amount), note.strip())
    )
    conn.commit()
    return cur.lastrowid


def select_user_categories(conn: sqlite3.Connection, user_id: int) -> List[str]:
    """
    Return distinct categories used by a given user (no defaults merged).

    Parameters
    ----------
    conn : sqlite3.Connection
        Open SQLite connection.
    user_id : int
        Telegram user identifier.

    Returns
    -------
    list of str
        Sorted case-insensitive distinct categories for the user.
    """
    cur = conn.execute(
        "SELECT DISTINCT category FROM expenses WHERE user_id = ? ORDER BY category COLLATE NOCASE",
        (user_id,)
    )
    return [row["category"] for row in cur.fetchall()]


def select_user_stores(conn: sqlite3.Connection, user_id: int) -> List[str]:
    """
    Return distinct stores used by a given user (no defaults merged).

    Parameters
    ----------
    conn : sqlite3.Connection
        Open SQLite connection.
    user_id : int
        Telegram user identifier.

    Returns
    -------
    list of str
        Sorted case-insensitive distinct stores for the user.
    """
    cur = conn.execute(
        "SELECT DISTINCT store FROM expenses WHERE user_id = ? ORDER BY store COLLATE NOCASE",
        (user_id,)
    )
    return [row["store"] for row in cur.fetchall()]


def select_last_n(conn: sqlite3.Connection, user_id: int, n: int = 10, offset: int = 0):
    """
    Fetch last N expenses by created_at (DESC).

    Parameters
    ----------
    conn : sqlite3.Connection
        Open SQLite connection.
    user_id : int
        Telegram user identifier.
    n : int, optional
        Number of rows to fetch, by default 10.
    offset : int, optional
        Offset for pagination, by default 0.

    Returns
    -------
    list of sqlite3.Row
        Rows ordered by datetime(created_at) DESC.
    """
    cur = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY datetime(created_at) DESC LIMIT ? OFFSET ?",
        (user_id, n, offset)
    )
    return cur.fetchall()
