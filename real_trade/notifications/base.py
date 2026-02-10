#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
BaseNotifier - 通知基类

定义统一的通知接口。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from typing import Any, Dict, Optional


class BaseNotifier:
    """
    通知基类

    所有通知渠道继承此类，实现 send() 方法。
    """

    def __init__(self, name: str = "base"):
        self.name = name
        self.enabled = True

    def send(
        self, message: str, level: str = "info", extra: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        发送通知

        Args:
            message: 通知内容
            level: 通知级别 ("info", "warn", "error", "critical")
            extra: 附加数据

        Returns:
            是否发送成功
        """
        raise NotImplementedError

    def send_trade(
        self,
        symbol: str,
        side: str,
        size: float,
        price: float,
        pnl: Optional[float] = None,
    ):
        """发送交易通知（便捷方法）"""
        msg = f"[{side.upper()}] {symbol}  size={size:.6f}  price={price:.4f}"
        if pnl is not None:
            msg += f"  pnl={pnl:.4f}"
        return self.send(msg, level="info")

    def send_alert(self, message: str):
        """发送告警"""
        return self.send(f"[ALERT] {message}", level="warn")

    def send_error(self, message: str):
        """发送错误通知"""
        return self.send(f"[ERROR] {message}", level="error")
