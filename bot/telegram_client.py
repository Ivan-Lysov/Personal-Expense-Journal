import json
import os
import urllib.request
import urllib.error
from typing import Any, Dict, Optional


from dotenv import load_dotenv
load_dotenv()


def _ensure_base_uri() -> str:
    """
    Resolve TELEGRAM_BASE_URI from env or build it from BOT_TOKEN.

    Returns
    -------
    str
        Base URI like 'https://api.telegram.org/bot<token>'.
    """
    base = os.getenv("TELEGRAM_BASE_URI")
    if base:
        return base.rstrip("/")
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Neither TELEGRAM_BASE_URI nor BOT_TOKEN is set")
    return f"https://api.telegram.org/bot{token}"


def _request(method: str, **params: Any) -> Dict[str, Any]:
    """
    Perform a Bot API request and return the 'result' payload.

    Parameters
    ----------
    method : str
        Bot API method name (e.g., 'sendMessage').
    **params : Any
        JSON-serializable method parameters.

    Returns
    -------
    dict
        Telegram 'result' JSON.

    Raises
    ------
    RuntimeError
        If Telegram returned ok=False or non-200 HTTP.
    """
    base_uri = _ensure_base_uri()
    url = f"{base_uri}/{method}"
    data = json.dumps(params).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            payload = json.loads(body)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTPError for {method}: {e.code} {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"URLError for {method}: {e.reason}") from e

    if not isinstance(payload, dict) or payload.get("ok") is not True:
        desc = payload.get("description") if isinstance(payload, dict) else None
        raise RuntimeError(f"Telegram error for {method}: {desc or 'unknown error'}")
    return payload["result"]


def getUpdates(**params: Any) -> Dict[str, Any]:
    """
    Fetch updates (long polling friendly).

    Parameters
    ----------
    **params : Any
        getUpdates parameters: offset, timeout, limit, allowed_updates, etc.

    Returns
    -------
    dict
        Raw 'result' from Telegram (list of updates).
    """
    return _request("getUpdates", **params)


def sendMessage(chat_id: int, text: str, **params: Any) -> Dict[str, Any]:
    """
    Send a text message.

    Parameters
    ----------
    chat_id : int
        Target chat id.
    text : str
        Message text.
    **params : Any
        Additional Bot API fields, e.g. reply_markup (dict),
        parse_mode, disable_notification, etc.

    Returns
    -------
    dict
        Sent message object.
    """
    return _request("sendMessage", chat_id=chat_id, text=text, **params)


def answerCallbackQuery(callback_query_id: str, **params: Any) -> Dict[str, Any]:
    """
    Answer a callback query (for inline button clicks).

    Parameters
    ----------
    callback_query_id : str
        Callback query identifier from update.callback_query.id.
    **params : Any
        Optional: text, show_alert, url, cache_time.

    Returns
    -------
    dict
        True-like result from Telegram.
    """
    return _request("answerCallbackQuery", callback_query_id=callback_query_id, **params)


def sendSticker(chat_id: int, sticker_file_id: str, **params: Any) -> Dict[str, Any]:
    """
    Send a sticker (by file_id).

    Parameters
    ----------
    chat_id : int
        Target chat id.
    sticker_file_id : str
        Sticker file_id.
    **params : Any
        Optional Bot API fields.

    Returns
    -------
    dict
        Sent message object.
    """
    return _request("sendSticker", chat_id=chat_id, sticker=sticker_file_id, **params)


def sendPhoto(chat_id: int, photo_file_id: str, **params: Any) -> Dict[str, Any]:
    """
    Send a photo (by file_id).

    Parameters
    ----------
    chat_id : int
        Target chat id.
    photo_file_id : str
        Photo file_id.
    **params : Any
        Optional Bot API fields, e.g. caption, reply_markup.

    Returns
    -------
    dict
        Sent message object.
    """
    return _request("sendPhoto", chat_id=chat_id, photo=photo_file_id, **params)


def getMe() -> Dict[str, Any]:
    """
    Get bot information.

    Returns
    -------
    dict
        Bot user info.
    """
    return _request("getMe")


def deleteMessage(chat_id: int, message_id: int) -> Dict[str, Any]:
    """
    Delete bot's own message in a chat.

    Parameters
    ----------
    chat_id : int
        Target chat id.
    message_id : int
        Message id to delete.

    Returns
    -------
    dict
        True-like result.
    """
    return _request("deleteMessage", chat_id=chat_id, message_id=message_id)


def editMessageReplyMarkup(
    chat_id: int, message_id: int, reply_markup: Optional[Dict[str, Any]] = None) \
        -> Dict[str, Any]:
    """
    Edit (or clear) inline keyboard of an existing message.

    Parameters
    ----------
    chat_id : int
        Target chat id.
    message_id : int
        Message id whose keyboard to edit.
    reply_markup : dict or None
        New keyboard dict, or None to clear.

    Returns
    -------
    dict
        Edited message object (or True).
    """
    params: Dict[str, Any] = {"chat_id": chat_id, "message_id": message_id}
    if reply_markup is not None:
        params["reply_markup"] = reply_markup
    return _request("editMessageReplyMarkup", **params)
