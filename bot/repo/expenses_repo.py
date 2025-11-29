import sqlite3
from typing import List


def insert_expense(
    conn: sqlite3.Connection, user_id: int, category: str, store: str, amount: float, note: str = ""
) -> int:
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
        (user_id, category.strip(), store.strip(), float(amount), note.strip()),
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
        "SELECT DISTINCT category FROM expenses WHERE user_id = ? ORDER BY category COLLATE NOCASE", (user_id,)
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
        "SELECT DISTINCT store FROM expenses WHERE user_id = ? ORDER BY store COLLATE NOCASE", (user_id,)
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
        (user_id, n, offset),
    )
    return cur.fetchall()


def sum_last_n(conn: sqlite3.Connection, user_id: int, n: int = 10) -> float:
    """
    Sum amounts of the last N expenses by created_at (DESC).

    Parameters
    ----------
    conn : sqlite3.Connection
        Open SQLite connection.
    user_id : int
        Telegram user identifier.
    n : int, optional
        Number of recent rows to sum, by default 10.

    Returns
    -------
    float
        Sum of amounts (0.0 if no rows).
    """
    cur = conn.execute(
        """
        SELECT COALESCE(SUM(amount), 0.0) AS s
        FROM (
          SELECT amount
          FROM expenses
          WHERE user_id = ?
          ORDER BY datetime(created_at) DESC
          LIMIT ?
        ) t
        """,
        (user_id, n),
    )
    row = cur.fetchone()
    return float(row["s"] if row and row["s"] is not None else 0.0)


def monthly_report_by_category(
    conn: sqlite3.Connection,
    user_id: int,
    year: int | None = None,
    month: int | None = None,
) -> tuple[List[sqlite3.Row], float, str]:
    """
    Aggregate monthly expenses by category for a given user.

    If ``year`` and ``month`` are not provided, the current month is used
    based on the server's local time (Python datetime, not SQLite).

    Parameters
    ----------
    conn : sqlite3.Connection
        Open SQLite connection with row_factory=sqlite3.Row.
    user_id : int
        Telegram user identifier.
    year : int, optional
        Year in ``YYYY`` format. If None, current year is used.
    month : int, optional
        Month in ``1..12``. If None, current month is used.

    Returns
    -------
    rows : list of sqlite3.Row
        Rows with columns: ``category`` and ``total`` (sum of amounts).
    total : float
        Total sum of all categories for the month (0.0 if no rows).
    month_key : str
        Month key in ``YYYY-MM`` format used in the query.

    """
    from datetime import datetime

    if year is not None and month is not None:
        month_key = f"{int(year):04d}-{int(month):02d}"
    else:
        # Use current UTC month as a simple approximation
        month_key = datetime.utcnow().strftime("%Y-%m")

    # Per-category aggregates
    cur = conn.execute(
        """
        SELECT category,
               SUM(amount) AS total
        FROM expenses
        WHERE user_id = ?
          AND strftime('%Y-%m', created_at) = ?
        GROUP BY category
        ORDER BY total DESC;
        """,
        (user_id, month_key),
    )
    rows = cur.fetchall()

    # Overall total for the month
    cur_total = conn.execute(
        """
        SELECT SUM(amount) AS total
        FROM expenses
        WHERE user_id = ?
          AND strftime('%Y-%m', created_at) = ?
        """,
        (user_id, month_key),
    )
    row_total = cur_total.fetchone()
    if row_total and row_total["total"] is not None:
        total = float(row_total["total"])
    else:
        total = 0.0

    return rows, total, month_key


def select_all_for_user(conn: sqlite3.Connection, user_id: int) -> List[sqlite3.Row]:
    """
    Select all expense rows for a given user ordered by created_at ascending.

    Parameters
    ----------
    conn : sqlite3.Connection
        Open SQLite connection with row_factory=sqlite3.Row.
    user_id : int
        Telegram user identifier.

    Returns
    -------
    list of sqlite3.Row
        Rows with columns: created_at, category, store, amount, note.
    """
    cur = conn.execute(
        """
        SELECT created_at, category, store, amount, note
        FROM expenses
        WHERE user_id = ?
        ORDER BY datetime(created_at) ASC;
        """,
        (user_id,),
    )
    return cur.fetchall()
