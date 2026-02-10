#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Notifications - 通知模块

支持 Telegram、钉钉、Webhook、邮件等多种通知渠道。
"""

from .base import BaseNotifier
from .dingtalk import DingTalkNotifier
from .email_notify import EmailNotifier
from .telegram import TelegramNotifier
from .webhook import WebhookNotifier

__all__ = [
    "BaseNotifier",
    "TelegramNotifier",
    "DingTalkNotifier",
    "WebhookNotifier",
    "EmailNotifier",
]
