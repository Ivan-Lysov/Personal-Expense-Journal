import json
import sqlite3
from typing import Tuple, Dict, Any

def get_state(conn: sqlite3.Connection, user_id: int) -> Tuple[str, Dict[str, Any]]:
    """
    Read FSM state and payload for a given user.

    Parameters
    ----------
    conn : sqlite3.Connection
        Open SQLite connection.
    user_id : int
        Telegram user identifier.

    Returns
    -------
    tuple[str, dict]
        (state, payload_dict). Defaults to ("IDLE", {}) if no row exists.
    """
    cur = conn.execute("SELECT state, payload FROM user_state WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if not row:
        return "IDLE", {}
    try:
        payload = json.loads(row["payload"]) if row["payload"] else {}
    except Exception:
        payload = {}
    return row["state"], payload


def set_state(conn: sqlite3.Connection, user_id: int, state: str, payload: Dict[str, Any]) -> None:
    """
    Upsert FSM state and payload for a given user.

    Parameters
    ----------
    conn : sqlite3.Connection
        Open SQLite connection.
    user_id : int
        Telegram user identifier.
    state : str
        FSM state name.
    payload : dict
        JSON-serializable payload.

    Returns
    -------
    None
    """
    payload_str = json.dumps(payload, ensure_ascii=False)
    conn.execute(
        "INSERT INTO user_state(user_id, state, payload) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET state=excluded.state, payload=excluded.payload",
        (user_id, state, payload_str)
    )
    conn.commit()


def reset_state(conn: sqlite3.Connection, user_id: int) -> None:
    """
    Reset FSM state to IDLE and clear payload.

    Parameters
    ----------
    conn : sqlite3.Connection
        Open SQLite connection.
    user_id : int
        Telegram user identifier.

    Returns
    -------
    None
    """
    conn.execute(
        "INSERT INTO user_state(user_id, state, payload) VALUES (?, 'IDLE', '{}') "
        "ON CONFLICT(user_id) DO UPDATE SET state='IDLE', payload='{}'",
        (user_id,)
    )
    conn.commit()
