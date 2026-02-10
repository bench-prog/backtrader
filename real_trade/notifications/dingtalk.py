#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
DingTalkNotifier - 钉钉机器人通知
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import base64
import hashlib
import hmac
import json
import time
import urllib.request
from typing import Any, Dict, Optional

from .base import BaseNotifier


class DingTalkNotifier(BaseNotifier):
    """
    钉钉机器人通知

    Usage::

        notifier = DingTalkNotifier(
            webhook_url="https://oapi.dingtalk.com/robot/send?access_token=xxx",
            secret="SECxxx",  # 可选，加签密钥
        )
        notifier.send("Hello from trading bot!")
    """

    def __init__(self, webhook_url: str, secret: Optional[str] = None):
        super().__init__(name="dingtalk")
        self.webhook_url = webhook_url
        self.secret = secret

    def _sign_url(self) -> str:
        """对 webhook URL 加签"""
        if not self.secret:
            return self.webhook_url

        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            self.secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        sign = base64.b64encode(hmac_code).decode("utf-8")

        sep = "&" if "?" in self.webhook_url else "?"
        return f"{self.webhook_url}{sep}timestamp={timestamp}&sign={sign}"

    def send(
        self, message: str, level: str = "info", extra: Optional[Dict[str, Any]] = None
    ) -> bool:
        if not self.enabled:
            return False

        try:
            url = self._sign_url()
            payload = json.dumps(
                {
                    "msgtype": "text",
                    "text": {"content": message},
                }
            ).encode("utf-8")

            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=10)
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("errcode", -1) == 0
        except Exception as e:
            print(f"[DingTalk] Send failed: {e}")
            return False
