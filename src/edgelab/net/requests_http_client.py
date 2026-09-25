"""Real HttpClient implementation, wrapping the `requests` library.

Every collector so far (edgar_8k.py) is written against a small
HttpClient Protocol and tested exclusively with fakes -- deliberately,
so collector logic is testable without live network access. This
module is the one place that protocol is backed by a real network
call, so it is the only new thing STORY-008 does *not* unit-test
against a live SEC response (this sandbox's network egress cannot
reach data.sec.gov, per every earlier collector's own docstring) --
it is exercised for real the first time it runs on the Pi.

Story: stories/STORY-008-pi-collector-entrypoint.md
"""

from __future__ import annotations

import requests


class RequestsHttpClient:
    """Implements edgar_8k.py's HttpClient protocol using `requests`.

    Structurally satisfies the protocol: `.get(url, *, headers,
    timeout)` returning an object with `.status_code`, `.content` and
    `.json()` -- `requests.Response` already has all three, so no
    adapter object is needed.
    """

    def get(self, url: str, *, headers: dict, timeout: float) -> requests.Response:
        return requests.get(url, headers=headers, timeout=timeout)
