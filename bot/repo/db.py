import sqlite3

def get_connection(db_path: str) -> sqlite3.Connection:
    """
    Open a SQLite connection with a consistent configuration.

    Parameters
    ----------
    db_path : str
        Path to the SQLite database file.

    Returns
    -------
    sqlite3.Connection
        Opened connection with row_factory and foreign_keys pragma enabled.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


DDL_EXPENSES = """
CREATE TABLE IF NOT EXISTS expenses (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id    INTEGER NOT NULL,
  created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')), -- UTC ISO-8601
  category   TEXT    NOT NULL,
  store      TEXT    NOT NULL,
  amount     REAL    NOT NULL CHECK (amount > 0),
  note       TEXT    DEFAULT ''
);
"""

DDL_USER_STATE = """
CREATE TABLE IF NOT EXISTS user_state (
  user_id INTEGER PRIMARY KEY,
  state   TEXT    NOT NULL,
  payload TEXT    NOT NULL DEFAULT '{}'
);
"""

def init_schema(conn: sqlite3.Connection) -> None:
    """
    Create minimal tables (expenses, user_state).

    Parameters
    ----------
    conn : sqlite3.Connection
        Open SQLite connection.

    Returns
    -------
    None
    """
    conn.executescript(DDL_EXPENSES)
    conn.executescript(DDL_USER_STATE)
    conn.commit()
