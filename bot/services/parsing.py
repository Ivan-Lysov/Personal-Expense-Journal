# bot/services/parsing.py
from typing import Optional


def parse_amount(text: str) -> Optional[float]:
    """
    Parse user-entered amount from a free-form string.

    This parser is intentionally simple for MVP:
    - strips whitespace,
    - replaces comma with dot,
    - rejects negative or zero,
    - returns None on failure.

    Parameters
    ----------
    text : str
        Raw user-entered text (e.g. "125,50", "  200.0 ").

    Returns
    -------
    float or None
        Parsed positive float if valid, otherwise None.
    """
    if not isinstance(text, str):
        return None
    s = text.strip().replace(",", ".")
    # Allow leading "+"; reject minus
    if s.startswith("+"):
        s = s[1:].lstrip()

    # Reject empty or non-numeric forms quickly
    try:
        value = float(s)
    except Exception:
        return None

    if value <= 0:
        return None
    return value
