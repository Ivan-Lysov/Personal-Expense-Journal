import json
import os
from typing import Any, Dict, List
import urllib.request
from urllib.error import HTTPError

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env var is required (export BOT_TOKEN=...)")

BASE_URI = f"https://api.telegram.org/bot{BOT_TOKEN}"


def _request(method: str, **params) -> Dict[str, Any]:
    """
    Call Telegram Bot API method with JSON body.

    Parameters
    ----------
    method : str
        Bot API method name (e.g. 'getUpdates', 'sendMessage').
    **params :
        JSON-serializable parameters.

    Returns
    -------
    dict
        'result' field from Telegram API response.

    Raises
    ------
    RuntimeError
        If Telegram returns HTTP error or ok == False with description.
    """
    data = json.dumps(params).encode("utf-8")

    req = urllib.request.Request(
        url=f"{BASE_URI}/{method}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
    except HTTPError as e:
        try:
            error_body = e.read().decode("utf-8", errors="ignore")
        except Exception:
            error_body = "<no body>"
        raise RuntimeError(
            f"HTTPError for {method}: {e.code} {e.reason}, body={error_body}"
        ) from e

    payload = json.loads(body)

    if not payload.get("ok", False):
        desc = payload.get("description", "no description")
        raise RuntimeError(
            f"Telegram API error for {method}: {desc} (payload={payload})"
        )

    return payload["result"]


def getUpdates(**params) -> List[Dict[str, Any]]:
    """
    Wrapper around getUpdates.

    Parameters
    ----------
    **params :
        Any valid getUpdates parameter (offset, timeout, etc).

    Returns
    -------
    list of dict
        List of update objects.
    """
    return _request("getUpdates", **params)


def sendMessage(chat_id: int, text: str, **params) -> Dict[str, Any]:
    """
    Wrapper around sendMessage.

    Parameters
    ----------
    chat_id : int
        Target chat id.
    text : str
        Message text.
    **params :
        Any optional parameters (parse_mode, reply_markup, etc).

    Returns
    -------
    dict
        Sent message object.
    """
    return _request("sendMessage", chat_id=chat_id, text=text, **params)


def answerCallbackQuery(callback_query_id: str, **params) -> Dict[str, Any]:
    """
    Wrapper around answerCallbackQuery.
    """
    return _request("answerCallbackQuery", callback_query_id=callback_query_id, **params)


def deleteMessage(chat_id: int, message_id: int) -> Dict[str, Any]:
    """
    Wrapper around deleteMessage.

    Parameters
    ----------
    chat_id : int
        Chat id where the message is.
    message_id : int
        Message id to delete.

    Returns
    -------
    dict
        True-like result.
    """
    return _request("deleteMessage", chat_id=chat_id, message_id=message_id)


def sendSticker(chat_id: int, sticker: str, **params) -> Dict[str, Any]:
    """
    Wrapper around sendSticker.
    """
    return _request("sendSticker", chat_id=chat_id, sticker=sticker, **params)


def sendPhoto(chat_id: int, photo: str, **params) -> Dict[str, Any]:
    """
    Wrapper around sendPhoto.
    """
    return _request("sendPhoto", chat_id=chat_id, photo=photo, **params)


def getMe() -> Dict[str, Any]:
    """
    Wrapper around getMe.
    """
    return _request("getMe")
