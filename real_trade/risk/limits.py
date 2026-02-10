#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
TradeLimiter - 交易限制

限制交易频率、单日亏损、最大持仓等，防止过度交易。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime


class TradeLimiter:
    """交易频率和亏损限制"""

    def __init__(
        self,
        max_daily_trades: int = 50,
        max_daily_loss: float = 0.0,  # 0=不限制
        cooldown_seconds: int = 0,  # 两笔交易最小间隔秒数
    ):
        self.max_daily_trades = max_daily_trades
        self.max_daily_loss = max_daily_loss
        self.cooldown_seconds = cooldown_seconds

        self.daily_trade_count = 0
        self.daily_pnl = 0.0
        self._current_date = None
        self._last_trade_time = None

    def _check_new_day(self):
        today = datetime.date.today()
        if self._current_date != today:
            self._current_date = today
            self.daily_trade_count = 0
            self.daily_pnl = 0.0

    def allow(self) -> bool:
        """是否允许开新仓"""
        self._check_new_day()

        if self.daily_trade_count >= self.max_daily_trades:
            return False

        if self.max_daily_loss > 0 and self.daily_pnl <= -self.max_daily_loss:
            return False

        if self.cooldown_seconds > 0 and self._last_trade_time:
            elapsed = (datetime.datetime.now() - self._last_trade_time).total_seconds()
            if elapsed < self.cooldown_seconds:
                return False

        return True

    def record(self, pnl: float = 0.0):
        """记录一笔交易"""
        self._check_new_day()
        self.daily_trade_count += 1
        self.daily_pnl += pnl
        self._last_trade_time = datetime.datetime.now()

    def reset(self):
        self.daily_trade_count = 0
        self.daily_pnl = 0.0
        self._last_trade_time = None
