#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
WebhookNotifier - 通用 Webhook 通知
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import json
import urllib.request
from typing import Any, Dict, Optional

from .base import BaseNotifier


class WebhookNotifier(BaseNotifier):
    """
    通用 Webhook 通知

    向指定 URL POST JSON 数据。

    Usage::

        notifier = WebhookNotifier(url="https://your-server.com/webhook")
        notifier.send("Trade executed!")
    """

    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None):
        super().__init__(name="webhook")
        self.url = url
        self.headers = headers or {}

    def send(
        self, message: str, level: str = "info", extra: Optional[Dict[str, Any]] = None
    ) -> bool:
        if not self.enabled:
            return False

        try:
            payload = {
                "timestamp": datetime.datetime.now().isoformat(),
                "level": level,
                "message": message,
            }
            if extra:
                payload["extra"] = extra

            data = json.dumps(payload).encode("utf-8")
            req_headers = {"Content-Type": "application/json"}
            req_headers.update(self.headers)

            req = urllib.request.Request(
                self.url,
                data=data,
                headers=req_headers,
            )
            resp = urllib.request.urlopen(req, timeout=10)
            return 200 <= resp.getcode() < 300
        except Exception as e:
            print(f"[Webhook] Send failed: {e}")
            return False
