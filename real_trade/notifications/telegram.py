#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
TelegramNotifier - Telegram Bot 通知
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

from .base import BaseNotifier


class TelegramNotifier(BaseNotifier):
    """
    Telegram Bot 通知

    Usage::

        notifier = TelegramNotifier(
            bot_token="YOUR_BOT_TOKEN",
            chat_id="YOUR_CHAT_ID",
        )
        notifier.send("Hello from trading bot!")
    """

    def __init__(self, bot_token: str, chat_id: str, proxy: Optional[str] = None):
        super().__init__(name="telegram")
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.proxy = proxy
        self._base_url = f"https://api.telegram.org/bot{bot_token}"

    def send(
        self, message: str, level: str = "info", extra: Optional[Dict[str, Any]] = None
    ) -> bool:
        if not self.enabled:
            return False

        try:
            url = f"{self._base_url}/sendMessage"
            data = urllib.parse.urlencode(
                {
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                }
            ).encode("utf-8")

            req = urllib.request.Request(url, data=data)
            if self.proxy:
                proxy_handler = urllib.request.ProxyHandler(
                    {
                        "https": self.proxy,
                        "http": self.proxy,
                    }
                )
                opener = urllib.request.build_opener(proxy_handler)
            else:
                opener = urllib.request.build_opener()

            resp = opener.open(req, timeout=10)
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("ok", False)
        except Exception as e:
            print(f"[Telegram] Send failed: {e}")
            return False
