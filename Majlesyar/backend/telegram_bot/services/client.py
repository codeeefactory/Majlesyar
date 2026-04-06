from __future__ import annotations

import json
from typing import Any
from urllib import error, request

from django.conf import settings


class TelegramApiError(RuntimeError):
    pass


class TelegramApiClient:
    def __init__(self, token: str | None = None):
        self.token = token or settings.TELEGRAM_BOT["TOKEN"]

    @property
    def base_url(self) -> str:
        return f"https://api.telegram.org/bot{self.token}"

    def _request(self, method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        data = json.dumps(payload or {}).encode("utf-8")
        req = request.Request(f"{self.base_url}/{method}", data=data, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=30) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise TelegramApiError(f"{method} failed with HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise TelegramApiError(f"{method} failed: {exc.reason}") from exc

        body = json.loads(raw)
        if not body.get("ok"):
            raise TelegramApiError(f"{method} failed: {body}")
        return body["result"]

    def send_message(self, chat_id: int, text: str, reply_markup: dict[str, Any] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self._request("sendMessage", payload)

    def answer_callback_query(self, callback_query_id: str, text: str = "") -> dict[str, Any]:
        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        return self._request("answerCallbackQuery", payload)

    def edit_message_reply_markup(self, chat_id: int, message_id: int, reply_markup: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request(
            "editMessageReplyMarkup",
            {
                "chat_id": chat_id,
                "message_id": message_id,
                "reply_markup": reply_markup or {"inline_keyboard": []},
            },
        )

    def get_updates(self, offset: int | None = None, timeout: int = 30) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "timeout": timeout,
            "allowed_updates": ["message", "callback_query"],
        }
        if offset is not None:
            payload["offset"] = offset
        return self._request("getUpdates", payload)

    def set_webhook(self, url: str, secret_token: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "url": url,
            "allowed_updates": ["message", "callback_query"],
        }
        if secret_token:
            payload["secret_token"] = secret_token
        return self._request("setWebhook", payload)

    def delete_webhook(self) -> dict[str, Any]:
        return self._request("deleteWebhook", {"drop_pending_updates": False})

    def get_me(self) -> dict[str, Any]:
        return self._request("getMe")

