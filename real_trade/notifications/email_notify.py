#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
EmailNotifier - 邮件通知
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import smtplib
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

from .base import BaseNotifier


class EmailNotifier(BaseNotifier):
    """
    邮件通知

    Usage::

        notifier = EmailNotifier(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            username="you@gmail.com",
            password="app_password",
            to_addr="alert@example.com",
        )
        notifier.send("Trade executed!")
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int = 587,
        username: str = "",
        password: str = "",
        from_addr: Optional[str] = None,
        to_addr: str = "",
        use_tls: bool = True,
        subject_prefix: str = "[Trading Bot]",
    ):
        super().__init__(name="email")
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr or username
        self.to_addr = to_addr
        self.use_tls = use_tls
        self.subject_prefix = subject_prefix

    def send(
        self, message: str, level: str = "info", extra: Optional[Dict[str, Any]] = None
    ) -> bool:
        if not self.enabled:
            return False

        try:
            subject = f"{self.subject_prefix} [{level.upper()}]"
            msg = MIMEText(message, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = self.from_addr
            msg["To"] = self.to_addr

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.username:
                    server.login(self.username, self.password)
                server.sendmail(self.from_addr, [self.to_addr], msg.as_string())

            return True
        except Exception as e:
            print(f"[Email] Send failed: {e}")
            return False
