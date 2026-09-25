"""Telegram sender -- a thin wrapper over Telegram's Bot API
sendMessage endpoint. Real network, like every other real-transport
class in this repository (RequestsHttpClient, YFinanceHistoryFetcher)
-- never exercised against live Telegram in this sandbox's tests,
only via FakeTelegramSender.

Story: stories/STORY-013-telegram-ops-notification.md
"""

from __future__ import annotations

from typing import Protocol

import requests


class TelegramSendError(RuntimeError):
    """Raised when Telegram's API returns a non-200 response."""


class TelegramSender(Protocol):
    def send(self, chat_id: str, text: str) -> None: ...


class RequestsTelegramSender:
    def __init__(self, bot_token: str, *, timeout: float = 10.0):
        self._bot_token = bot_token
        self._timeout = timeout

    def send(self, chat_id: str, text: str) -> None:
        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        response = requests.post(
            url, data={"chat_id": chat_id, "text": text}, timeout=self._timeout
        )
        if response.status_code != 200:
            raise TelegramSendError(
                f"Telegram API returned HTTP {response.status_code}: {response.text[:200]}"
            )


class FakeTelegramSender:
    """Records every call, sends nothing -- for tests."""

    def __init__(self) -> None:
        self.sent: list = []

    def send(self, chat_id: str, text: str) -> None:
        self.sent.append((chat_id, text))
